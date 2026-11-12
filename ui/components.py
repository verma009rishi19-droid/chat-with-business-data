"""Streamlit UI Reusable Components and Visualizers."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.graph.state import ChartSpec


def render_chart_component(chart_spec_dict: dict | None) -> None:
    """Render interactive Plotly chart from declarative JSON spec."""
    if not chart_spec_dict:
        return

    try:
        spec = ChartSpec(**chart_spec_dict)
    except Exception:
        return

    if spec.type == "none" or not spec.data:
        return

    df = pd.DataFrame(spec.data)
    if spec.x not in df.columns or spec.y not in df.columns:
        return

    st.markdown(f"#### 📊 {spec.title or 'Data Visualization'}")

    fig: go.Figure | None = None
    if spec.type == "bar":
        fig = px.bar(
            df,
            x=spec.x,
            y=spec.y,
            title=spec.title,
            labels=spec.labels,
            color_discrete_sequence=["#2E86AB"],
            template="plotly_white",
        )
    elif spec.type == "line":
        fig = px.line(
            df,
            x=spec.x,
            y=spec.y,
            title=spec.title,
            markers=True,
            line_shape="spline",
            color_discrete_sequence=["#06D6A0"],
            template="plotly_white",
        )
    elif spec.type == "pie":
        fig = px.pie(
            df,
            names=spec.x,
            values=spec.y,
            title=spec.title,
            template="plotly_white",
        )

    if fig:
        fig.update_layout(
            margin=dict(l=10, r=10, t=35, b=10),
            hovermode="x unified" if spec.type == "line" else "closest",
        )
        st.plotly_chart(fig, use_container_width=True)


def render_sql_inspector(sql_query: str | None, columns: list[str] | None, row_count: int, execution_ms: float) -> None:
    """Render collapsible SQL inspection card."""
    if not sql_query:
        return

    with st.expander(f"🔍 Show Generated SQL Query ({row_count} rows in {execution_ms:.1f}ms)"):
        st.code(sql_query, language="sql")
        if columns:
            st.caption(f"**Returned Columns:** {', '.join(columns)}")


def render_sources_inspector(sources: list[dict] | None) -> None:
    """Render collapsible reference documentation citations."""
    if not sources:
        return

    with st.expander(f"📚 Supporting Documentation ({len(sources)} citations)"):
        for s in sources:
            st.markdown(
                f"- **{s.get('title', 'Document')}** (`{s.get('doc_id', 'UNKNOWN')}`) — *{s.get('section', 'General')}*\n"
                f"  `Source:` {s.get('source', '')} | `Relevance Score:` {s.get('score', 0.0):.2f}"
            )
