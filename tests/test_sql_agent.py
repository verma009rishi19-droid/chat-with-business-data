"""Unit and Integration Tests for Text-to-SQL Agent Execution."""

from __future__ import annotations

from typing import Any

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult

from app.config import settings
from app.nodes.sql_agent import execute_sql, generate_sql_query


@pytest.fixture(autouse=True)
def setup_sqlite_env():
    """Ensure tests run against local populated database."""
    settings.DB_TYPE = "sqlite"


def test_execute_valid_analytical_query():
    """Test executing a valid business aggregation query."""
    query = """
    SELECT c.category_name, COUNT(o.order_id) as total_orders, ROUND(SUM(oi.total_price), 2) as gmv
    FROM categories c
    JOIN products p ON c.category_id = p.category_id
    JOIN order_items oi ON p.product_id = oi.product_id
    JOIN orders o ON oi.order_id = o.order_id
    GROUP BY c.category_name
    ORDER BY gmv DESC
    """
    res = execute_sql(query, dialect="sqlite")

    assert res.error is None
    assert res.row_count > 0
    assert "category_name" in res.columns
    assert "gmv" in res.columns
    assert res.execution_time_ms > 0


def test_execute_sourdough_quarterly_trend():
    """Test SQL query isolating the Q3 Artisanal Sourdough sales anomaly."""
    query = """
    SELECT strftime('%m', o.order_timestamp) as month, COUNT(oi.item_id) as units_sold
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.order_id
    WHERE oi.product_id = 'PROD-017'
    GROUP BY strftime('%m', o.order_timestamp)
    ORDER BY month ASC
    """
    res = execute_sql(query, dialect="sqlite")

    assert res.error is None
    assert res.row_count > 0
    # Map months to sold counts
    month_data = {row[0]: row[1] for row in res.rows}
    # Check that July (07), August (08), September (09) are drastically lower than June (06)
    jun = month_data.get("06", 0)
    jul = month_data.get("07", 0)
    assert jun > jul * 2, f"June sourdough sales ({jun}) should be > 2x July ({jul}) due to recall"


def test_execute_guardrail_blocks_drop_attempt():
    """Test that a destructive DROP statement passed to execute_sql is stopped cold."""
    malicious_query = "DROP TABLE customers"
    res = execute_sql(malicious_query, dialect="sqlite")

    assert res.error is not None
    assert "security violation" in res.error.lower()
    assert res.row_count == 0


class RecordingFakeChatModel(FakeListChatModel):
    last_prompt: str = ""

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        self.last_prompt = " ".join(str(m.content) for m in messages)
        return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)


def test_generate_sql_query_with_mock_llm():
    """Test prompt assembly and mock LLM invocation."""
    fake_llm = RecordingFakeChatModel(
        responses=["SELECT product_name, unit_price FROM products ORDER BY unit_price DESC LIMIT 5"]
    )

    sql = generate_sql_query("What are the 5 most expensive products?", llm=fake_llm)
    assert "SELECT product_name" in sql
    assert "What are the 5 most expensive products?" in fake_llm.last_prompt


def test_generate_sql_query_includes_error_feedback():
    """Test that retry error feedback is included in LLM context."""
    fake_llm = RecordingFakeChatModel(
        responses=["SELECT order_id, total_amount FROM orders LIMIT 10"]
    )

    generate_sql_query(
        "Show orders",
        llm=fake_llm,
        error_feedback="no such column: total_rev",
    )
    assert "no such column: total_rev" in fake_llm.last_prompt
