"""Unit Tests for Validator Node and Retry Management."""

from __future__ import annotations

from app.graph.state import AgentState
from app.nodes.validator import validate_agent_execution, validator_node


def test_validator_passes_on_valid_state():
    """Test validator accepts valid completed state."""
    state = AgentState(
        question="Total orders",
        route="SQL",
        sql_query="SELECT COUNT(*) FROM orders",
        sql_columns=["count"],
        sql_rows=[[14309]],
        sql_row_count=1,
        sql_error=None,
        answer="Total orders delivered were 14,309 [Table: orders].",
    )
    is_valid, err = validate_agent_execution(state)
    assert is_valid is True
    assert err is None


def test_validator_catches_sql_error_and_increments_retry():
    """Test validator rejects failed SQL query and increments retry_count."""
    state = AgentState(
        question="Show bad query",
        route="SQL",
        sql_query="SELECT nonexistent FROM orders",
        sql_error="no such column: nonexistent",
        retry_count=0,
        max_retries=2,
    )
    updates = validator_node(state)
    assert updates["is_valid"] is False
    assert updates["retry_count"] == 1
    assert "no such column" in updates["validation_error"]


def test_validator_fails_gracefully_at_max_retries():
    """Test validator halts retry loop after reaching max_retries."""
    state = AgentState(
        question="Repeated fail",
        route="SQL",
        sql_query="SELECT * FROM bad_tbl",
        sql_error="table bad_tbl does not exist",
        retry_count=1,
        max_retries=2,
    )
    updates = validator_node(state)
    assert updates["is_valid"] is True  # Terminate loop
    assert updates["retry_count"] == 2
    assert "Analysis Incomplete" in updates["answer"]
