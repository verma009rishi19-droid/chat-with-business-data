"""Unit Tests for Analyst Node, Plotly JSON Rendering, and Grounding."""

from __future__ import annotations

import plotly.graph_objects as go

from app.graph.state import ChartSpec
from app.nodes.analyst import build_chart_spec_from_sql, render_plotly_figure, run_analyst


def test_build_chart_spec_from_sql():
    """Test generating declarative JSON spec from relational tabular results."""
    cols = ["month", "revenue"]
    rows = [["2025-01", 12000.0], ["2025-02", 14500.0], ["2025-03", 19000.0]]

    spec = build_chart_spec_from_sql(cols, rows, title="Monthly Revenue")
    assert spec.type == "line"
    assert spec.x == "month"
    assert spec.y == "revenue"
    assert len(spec.data) == 3


def test_render_plotly_figure_from_json_spec():
    """Test rendering Plotly figure safely without code execution."""
    spec = ChartSpec(
        type="bar",
        title="Category Orders",
        x="category",
        y="orders",
        data=[
            {"category": "Fresh Produce", "orders": 4500},
            {"category": "Dairy", "orders": 3800},
            {"category": "Bakery", "orders": 2100},
        ],
    )

    fig = render_plotly_figure(spec)
    assert fig is not None
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    assert fig.data[0].type == "bar"


def test_render_empty_or_none_spec():
    """Test that empty or 'none' specs return None safely."""
    empty_spec = ChartSpec(type="none")
    assert render_plotly_figure(empty_spec) is None


def test_run_analyst_deterministic_citations():
    """Test analyst generates citations in deterministic fallback mode."""
    res = run_analyst(
        question="What was Q1 GMV?",
        sql_query="SELECT SUM(total_amount) FROM orders WHERE order_timestamp BETWEEN '2025-01-01' AND '2025-03-31'",
        columns=["gmv"],
        rows=[[354000.50]],
        retrieved_context=None,
    )
    assert res.answer is not None
    assert "[Table:" in res.answer or "orders" in res.answer.lower()
