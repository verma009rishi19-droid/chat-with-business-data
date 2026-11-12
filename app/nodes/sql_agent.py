"""Text-to-SQL Agent Node with Guardrail Validation and Execution."""

from __future__ import annotations

import logging
import time
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.config import settings
from app.db.connection import get_engine
from app.db.guardrails import validate_and_sanitize_sql
from app.db.schema_context import get_schema_context_prompt
from app.llm.factory import get_llm

logger = logging.getLogger(__name__)

SQL_SYSTEM_PROMPT = """You are an expert Data Engineer and SQL Analyst for a Quick-Commerce company (similar to Blinkit).
Your job is to write a single, optimal, read-only SQL SELECT statement that accurately answers the user's business question.

=== DATABASE SCHEMA & BUSINESS CONTEXT ===
{schema_context}

=== RULES & CONSTRAINTS ===
1. Return ONLY the raw SQL SELECT statement. No markdown code blocks (no ```sql), no explanation, no comments.
2. Never write INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, or DDL commands.
3. Do not include SQL comments (-- or /* */).
4. Only query the tables explicitly defined in the schema. Do not query system tables or catalogs.
5. Ensure date filters match the business calendar (e.g., Q1 = Jan-Mar, Q2 = Apr-Jun, Q3 = Jul-Sep, Q4 = Oct-Dec 2025).
6. When calculating averages (like AOV), handle NULLs and division safely.
7. Use the EXACT column names and recognized enum/string values provided in the schema context.
{error_feedback}
"""


class SQLAgentResult(BaseModel):
    sql_query: str = ""
    columns: list[str] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)
    row_count: int = 0
    error: str | None = None
    execution_time_ms: float = 0.0


def generate_sql_query(
    question: str,
    llm: BaseChatModel | None = None,
    error_feedback: str | None = None,
) -> str:
    """Invoke LLM to generate raw SQL SELECT statement."""
    model = llm or get_llm(temperature=0.0)
    schema_prompt = get_schema_context_prompt()

    feedback_section = ""
    if error_feedback:
        feedback_section = f"\n=== PREVIOUS ATTEMPT FAILED WITH ERROR ===\n{error_feedback}\nPlease correct this mistake in your query."

    prompt = ChatPromptTemplate.from_messages([
        ("system", SQL_SYSTEM_PROMPT),
        ("human", "Business Question: {question}"),
    ])

    chain = prompt | model
    response = chain.invoke({
        "schema_context": schema_prompt,
        "error_feedback": feedback_section,
        "question": question,
    })

    raw_sql = response.content.strip() if hasattr(response, "content") else str(response).strip()
    return raw_sql


def execute_sql(
    query: str,
    dialect: str | None = None,
) -> SQLAgentResult:
    """Validate query via SQLGlot AST guardrails and execute on read-only database engine."""
    active_dialect = dialect or ("sqlite" if settings.DB_TYPE == "sqlite" else "postgres")
    start_time = time.perf_counter()

    # Step 1: Guardrail Validation
    val_result = validate_and_sanitize_sql(query, dialect=active_dialect)
    if not val_result.is_valid:
        logger.warning("Guardrail rejected SQL query: %s", val_result.error)
        return SQLAgentResult(
            sql_query=query,
            error=val_result.error,
            execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2),
        )

    sanitized_sql = val_result.sanitized_sql

    # Step 2: Database Execution with read-only connection
    try:
        engine = get_engine(readonly=True)
        with engine.connect() as conn:
            cursor_res = conn.execute(text(sanitized_sql))
            columns = list(cursor_res.keys())
            raw_rows = cursor_res.fetchall()
            # Convert row values to JSON-serializable primitives
            serializable_rows = [
                [float(val) if hasattr(val, "as_integer_ratio") else (str(val) if val is not None else None) for val in r]
                for r in raw_rows
            ]

        execution_duration = round((time.perf_counter() - start_time) * 1000, 2)
        return SQLAgentResult(
            sql_query=sanitized_sql,
            columns=columns,
            rows=serializable_rows,
            row_count=len(serializable_rows),
            error=None,
            execution_time_ms=execution_duration,
        )
    except Exception as e:
        logger.error("Database query execution error: %s", e)
        return SQLAgentResult(
            sql_query=sanitized_sql,
            error=f"Database execution error: {e!s}",
            execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2),
        )


def run_sql_agent(
    question: str,
    llm: BaseChatModel | None = None,
    error_feedback: str | None = None,
) -> SQLAgentResult:
    """Full SQL Agent pipeline: Prompt -> Generation -> Validation -> Execution."""
    try:
        raw_sql = generate_sql_query(question, llm=llm, error_feedback=error_feedback)
    except Exception as e:
        logger.error("LLM SQL generation error: %s", e)
        return SQLAgentResult(error=f"LLM generation failed: {e!s}")

    return execute_sql(raw_sql)


def sql_agent_node(state: Any, llm: BaseChatModel | None = None) -> dict:
    """LangGraph node execution for SQL Agent."""
    question = getattr(state, "question", "") if not isinstance(state, dict) else state.get("question", "")
    val_err = getattr(state, "validation_error", None) if not isinstance(state, dict) else state.get("validation_error")

    result = run_sql_agent(question=question, llm=llm, error_feedback=val_err)

    return {
        "sql_query": result.sql_query,
        "sql_columns": result.columns,
        "sql_rows": result.rows,
        "sql_row_count": result.row_count,
        "sql_error": result.error,
        "sql_execution_ms": result.execution_time_ms,
    }

