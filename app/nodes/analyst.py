"""Analyst Node: Synthesizes SQL and RAG outputs into grounded explanations and JSON chart specs."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.graph.state import AgentState, ChartSpec
from app.llm.factory import get_llm

logger = logging.getLogger(__name__)

ANALYST_SYSTEM_PROMPT = """You are a Principal Business Intelligence Analyst for a quick-commerce enterprise (similar to Blinkit).
Your task is to analyze the user's business question using the provided SQL query results and retrieved business documents.

=== RULES & GROUNDEDNESS REQUIREMENTS ===
1. GROUNDED FACTUALITY: Every statement you make MUST be directly supported by the SQL data rows or the retrieved business documents. Do NOT invent numbers or extrapolate unrecorded events.
2. CITATION MANDATE: Explicitly cite your evidence using markdown tags:
   - For database figures: cite `[Table: <table_name>]` (e.g., `[Table: orders]`, `[Table: deliveries]`).
   - For document policies/incidents: cite `[Doc: <doc_id>]` or `[Doc: <source_file>]` (e.g., `[Doc: KB-SUPP-2025-089]`).
3. TRANSPARENCY: If the available data cannot answer part of the question or if rows are empty, explicitly state what is missing instead of guessing.
4. STRUCTURE: Provide:
   - **Executive Summary**: 2-3 sentence high-level takeaway with key metrics.
   - **Data Insights**: Bullet points analyzing numerical trends with citations.
   - **Root Cause & Operational Context**: Explanations grounded in knowledge base records (if applicable).
5. DECLARATIVE CHART SPECIFICATION:
   - If the data is suitable for visual charting (e.g. time series, categories, rankings), output a declarative `chart_spec`:
     - `type`: 'bar' (for categories/rankings), 'line' (for time-series/monthly trends), 'pie' (for proportions), or 'none'.
     - `title`: descriptive chart title.
     - `x`: column name for x-axis.
     - `y`: column name for y-axis.
     - `data`: list of row dictionaries matching the data points.
   - If data has fewer than 2 points or is a single scalar number, set `type` to 'none'.
   - NEVER generate Python/JavaScript executable code for charts.
"""


class AnalystOutput(BaseModel):
    answer: str = Field(description="Structured markdown analysis with citations.")
    chart_spec: ChartSpec = Field(
        default_factory=ChartSpec,
        description="Declarative JSON specification for chart visualization.",
    )


def build_chart_spec_from_sql(
    columns: list[str],
    rows: list[list[Any]],
    title: str = "Business Analytics Trend",
) -> ChartSpec:
    """Deterministic fallback chart specification generator from tabular SQL rows."""
    if not columns or not rows or len(rows) < 2:
        return ChartSpec(type="none")

    df = pd.DataFrame(rows, columns=columns)
    col_x = columns[0]
    col_y = columns[1] if len(columns) > 1 else columns[0]

    # Detect if numeric
    is_time_series = any(k in col_x.lower() for k in ["month", "date", "day", "time", "quarter", "year"])
    chart_type = "line" if is_time_series else "bar"

    # Convert records to dict
    data_records = df.to_dict(orient="records")
    return ChartSpec(
        type=chart_type,
        title=title,
        x=col_x,
        y=col_y,
        data=data_records[:50],  # cap to top 50
    )


def render_plotly_figure(chart_spec: ChartSpec) -> go.Figure | None:
    """Render Plotly figure directly from declarative JSON spec without executing code."""
    if not chart_spec or chart_spec.type == "none" or not chart_spec.data:
        return None

    try:
        df = pd.DataFrame(chart_spec.data)
        if chart_spec.x not in df.columns or chart_spec.y not in df.columns:
            return None

        if chart_spec.type == "bar":
            fig = px.bar(
                df,
                x=chart_spec.x,
                y=chart_spec.y,
                title=chart_spec.title,
                labels=chart_spec.labels or {chart_spec.x: chart_spec.x, chart_spec.y: chart_spec.y},
                template="plotly_white",
            )
        elif chart_spec.type == "line":
            fig = px.line(
                df,
                x=chart_spec.x,
                y=chart_spec.y,
                title=chart_spec.title,
                markers=True,
                template="plotly_white",
            )
        elif chart_spec.type == "pie":
            fig = px.pie(
                df,
                names=chart_spec.x,
                values=chart_spec.y,
                title=chart_spec.title,
                template="plotly_white",
            )
        else:
            return None

        fig.update_layout(margin=dict(l=20, r=20, t=40, b=20))
        return fig
    except Exception as e:
        logger.error("Failed to render Plotly figure from spec: %s", e)
        return None


def run_analyst(
    question: str,
    sql_query: str | None = None,
    columns: list[str] | None = None,
    rows: list[list[Any]] | None = None,
    retrieved_context: str | None = None,
    llm: BaseChatModel | None = None,
) -> AnalystOutput:
    """Generate grounded written analysis and declarative chart spec."""
    # Format SQL results table
    sql_summary = "No SQL data was queried."
    if columns and rows is not None:
        if len(rows) == 0:
            sql_summary = f"SQL Query: {sql_query}\nResult: 0 rows returned."
        else:
            preview_rows = rows[:25]
            df = pd.DataFrame(preview_rows, columns=columns)
            try:
                table_str = df.to_markdown(index=False)
            except Exception:
                table_str = df.to_string(index=False)
            sql_summary = f"SQL Query:\n{sql_query}\n\nData Table ({len(rows)} total rows):\n{table_str}"

    docs_summary = retrieved_context or "No operational documents were retrieved."

    human_content = f"""User Question: {question}

=== EXECUTED SQL DATA RESULT ===
{sql_summary}

=== RETRIEVED OPERATIONAL DOCUMENTS ===
{docs_summary}
"""
    try:
        model = llm or get_llm(temperature=0.1)
        structured_llm = model.with_structured_output(AnalystOutput)
        prompt = ChatPromptTemplate.from_messages([
            ("system", ANALYST_SYSTEM_PROMPT),
            ("human", "{payload}"),
        ])
        chain = prompt | structured_llm
        output: AnalystOutput = chain.invoke({"payload": human_content})

        # Ensure chart data matches rows if model omitted data points
        if output.chart_spec.type != "none" and not output.chart_spec.data and columns and rows:
            fallback_spec = build_chart_spec_from_sql(columns, rows, title=output.chart_spec.title or "Data Chart")
            output.chart_spec.data = fallback_spec.data

        return output
    except Exception as e:
        logger.warning("LLM Analyst invocation failed: %s. Generating deterministic summary.", e)
        # Deterministic fallback response
        ans_lines = [
            "### Executive Summary",
            f"Analysis for: *{question}*",
        ]
        if rows and columns:
            ans_lines.append(f"\nQueried {len(rows)} records from the warehouse [Table: orders].")
            ans_lines.append(f"Top row sample: {dict(zip(columns, rows[0]))}")
        if retrieved_context and "<untrusted_document" in retrieved_context:
            ans_lines.append("\nSupporting operational context retrieved from documentation [Doc: business_knowledge_base].")

        chart = build_chart_spec_from_sql(columns or [], rows or [], title=f"Analysis: {question[:30]}")
        return AnalystOutput(
            answer="\n".join(ans_lines),
            chart_spec=chart,
        )


def analyst_node(state: AgentState, llm: BaseChatModel | None = None) -> dict:
    """LangGraph node execution for Analyst."""
    analyst_result = run_analyst(
        question=state.question,
        sql_query=state.sql_query,
        columns=state.sql_columns,
        rows=state.sql_rows,
        retrieved_context=state.retrieved_context,
        llm=llm,
    )
    return {
        "answer": analyst_result.answer,
        "chart_spec": analyst_result.chart_spec,
    }
