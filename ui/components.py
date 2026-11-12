"""Streamlit UI Reusable Components, Animations and Data Visualizers."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.graph.state import ChartSpec

# Enterprise Cyber/Data Color Palettes
DATA_PALETTE = ["#00F2FE", "#4FACFE", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899"]


def render_chart_component(chart_spec_dict: dict | None) -> None:
    """Render interactive Plotly chart with modern dark data-analyst aesthetics."""
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

    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, rgba(17, 24, 39, 0.8), rgba(30, 41, 59, 0.8));
            border: 1px solid rgba(0, 242, 254, 0.2);
            border-radius: 12px;
            padding: 16px 20px 8px 20px;
            margin: 14px 0;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
            animation: fadeIn 0.4s ease-out;
        ">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                <span style="font-weight: 700; font-size: 1.05rem; color: #F3F4F6; display: flex; align-items: center; gap: 8px;">
                    <span style="color: #00F2FE;">📊</span> {spec.title or 'Telemetry Analytics'}
                </span>
                <span style="
                    font-size: 0.72rem;
                    text-transform: uppercase;
                    letter-spacing: 0.08em;
                    color: #00F2FE;
                    background: rgba(0, 242, 254, 0.1);
                    border: 1px solid rgba(0, 242, 254, 0.3);
                    padding: 3px 8px;
                    border-radius: 20px;
                ">Interactive Plotly Spec</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    fig: go.Figure | None = None
    if spec.type == "bar":
        fig = px.bar(
            df,
            x=spec.x,
            y=spec.y,
            labels=spec.labels,
            color_discrete_sequence=DATA_PALETTE,
        )
        fig.update_traces(
            marker=dict(
                line=dict(width=1, color="rgba(0, 242, 254, 0.6)"),
                opacity=0.9,
            )
        )
    elif spec.type == "line":
        fig = px.line(
            df,
            x=spec.x,
            y=spec.y,
            markers=True,
            line_shape="spline",
            color_discrete_sequence=["#00F2FE"],
        )
        fig.update_traces(
            line=dict(width=3),
            marker=dict(size=8, color="#00F2FE", line=dict(width=2, color="#FFFFFF")),
        )
    elif spec.type == "pie":
        fig = px.pie(
            df,
            names=spec.x,
            values=spec.y,
            color_discrete_sequence=DATA_PALETTE,
            hole=0.45,  # Modern Donut chart
        )

    if fig:
        fig.update_layout(
            paper_bgcolor="rgba(15, 23, 42, 0.0)",
            plot_bgcolor="rgba(15, 23, 42, 0.0)",
            font=dict(family="Inter, -apple-system, sans-serif", color="#E2E8F0", size=12),
            margin=dict(l=15, r=15, t=25, b=25),
            hovermode="x unified" if spec.type == "line" else "closest",
            xaxis=dict(
                showgrid=True,
                gridcolor="rgba(255, 255, 255, 0.06)",
                showline=True,
                linecolor="rgba(255, 255, 255, 0.1)",
                tickfont=dict(color="#94A3B8"),
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor="rgba(255, 255, 255, 0.06)",
                showline=True,
                linecolor="rgba(255, 255, 255, 0.1)",
                tickfont=dict(color="#94A3B8"),
            ),
        )
        st.plotly_chart(fig, use_container_width=True)


def render_route_badge(route: str) -> None:
    """Render an animated glowing routing badge indicating agent collaboration."""
    badge_styles = {
        "SQL": ("⚡ SQL Engine", "rgba(0, 242, 254, 0.15)", "#00F2FE", "rgba(0, 242, 254, 0.3)"),
        "DOCS": ("📚 Knowledge RAG", "rgba(139, 92, 246, 0.15)", "#A78BFA", "rgba(139, 92, 246, 0.3)"),
        "BOTH": ("⚡ Relational SQL + 📚 Knowledge RAG", "rgba(16, 185, 129, 0.15)", "#34D399", "rgba(16, 185, 129, 0.3)"),
        "CLARIFY": ("🤝 Human-in-the-Loop", "rgba(245, 158, 11, 0.15)", "#FBBF24", "rgba(245, 158, 11, 0.3)"),
    }
    label, bg, color, border = badge_styles.get(route, ("🔍 Analytics Agent", "rgba(255,255,255,0.08)", "#E2E8F0", "rgba(255,255,255,0.15)"))

    st.markdown(
        f"""
        <div style="margin: 6px 0 12px 0;">
            <span style="
                background: {bg};
                color: {color};
                border: 1px solid {border};
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 0.76rem;
                font-weight: 600;
                letter-spacing: 0.04em;
                display: inline-flex;
                align-items: center;
                gap: 6px;
                box-shadow: 0 0 12px {bg};
            ">
                <span style="height: 6px; width: 6px; border-radius: 50%; background: {color}; box-shadow: 0 0 8px {color};"></span>
                {label}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sql_inspector(sql_query: str | None, columns: list[str] | None, row_count: int, execution_ms: float) -> None:
    """Render collapsible SQL inspection terminal with AST safety verification."""
    if not sql_query:
        return

    with st.expander(f"🛡️ Validated SQL Query AST ({row_count} rows in {execution_ms:.1f}ms)"):
        st.markdown(
            f"""
            <div style="font-size: 0.8rem; color: #94A3B8; margin-bottom: 8px;">
                <span style="color: #10B981; font-weight: 600;">✓ AST Validated</span> &nbsp;|&nbsp;
                <span>Engine: Read-Only Role</span> &nbsp;|&nbsp;
                <span>Rows: <strong style="color: #F1F5F9;">{row_count}</strong></span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.code(sql_query, language="sql")
        if columns:
            st.caption(f"**Schema Attributes:** `{', '.join(columns)}`")


def render_sources_inspector(sources: list[dict] | None) -> None:
    """Render collapsible reference documentation citations with confidence tags."""
    if not sources:
        return

    with st.expander(f"📑 Grounding Knowledge Sources ({len(sources)} citations verified)"):
        for s in sources:
            st.markdown(
                f"""
                <div style="
                    background: rgba(30, 41, 59, 0.4);
                    border-left: 3px solid #00F2FE;
                    padding: 8px 12px;
                    border-radius: 0 8px 8px 0;
                    margin-bottom: 8px;
                    font-size: 0.85rem;
                ">
                    <div style="font-weight: 600; color: #F1F5F9;">{s.get('title', 'Document')}</div>
                    <div style="color: #94A3B8; font-size: 0.78rem;">
                        <span>ID: <code>{s.get('doc_id', 'UNKNOWN')}</code></span> &nbsp;•&nbsp;
                        <span>Section: <em>{s.get('section', 'General')}</em></span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
