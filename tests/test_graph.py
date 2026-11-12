"""End-to-End Tests for LangGraph Analytics Orchestration Workflow."""

from __future__ import annotations

import pytest

from app.config import settings
from app.graph.workflow import app_graph
from app.rag.vector_store import ingest_knowledge_base


@pytest.fixture(scope="module", autouse=True)
def setup_graph_test_env():
    """Ensure local database and vector store are ready."""
    settings.DB_TYPE = "sqlite"
    ingest_knowledge_base(force_mock_embeddings=True)


def test_graph_sql_route():
    """Test full graph execution for purely quantitative question."""
    config = {"configurable": {"thread_id": "test_thread_sql_01"}}
    inputs = {
        "question": "What is the total count of orders in the database?",
        "thread_id": "test_thread_sql_01",
    }
    final_state = app_graph.invoke(inputs, config=config)

    assert final_state["route"] == "SQL"
    assert final_state["sql_query"] is not None
    assert final_state["sql_error"] is None
    assert len(final_state["sql_rows"]) > 0
    assert final_state["answer"] is not None
    assert final_state["is_valid"] is True


def test_graph_docs_route():
    """Test full graph execution for qualitative policy query."""
    config = {"configurable": {"thread_id": "test_thread_docs_01"}}
    inputs = {
        "question": "What is our corporate delivery SLA policy and compensation guidelines?",
        "thread_id": "test_thread_docs_01",
    }
    final_state = app_graph.invoke(inputs, config=config)

    assert final_state["route"] == "DOCS"
    assert len(final_state["retrieved_docs"]) > 0
    assert final_state["answer"] is not None
    assert final_state["is_valid"] is True


def test_graph_both_route_with_anomalies():
    """Test full graph execution for combined 'why' question with SQL data and RAG docs."""
    config = {"configurable": {"thread_id": "test_thread_both_01"}}
    inputs = {
        "question": "Which sourdough products had falling sales in Q3 and why was there a decline?",
        "thread_id": "test_thread_both_01",
    }
    final_state = app_graph.invoke(inputs, config=config)

    assert final_state["route"] == "BOTH"
    assert final_state["sql_query"] is not None
    assert len(final_state["retrieved_docs"]) > 0
    assert final_state["answer"] is not None
    assert final_state["is_valid"] is True


def test_graph_clarify_route():
    """Test that ambiguous input triggers clarification request."""
    config = {"configurable": {"thread_id": "test_thread_clarify_01"}}
    inputs = {
        "question": "trends",
        "thread_id": "test_thread_clarify_01",
    }
    final_state = app_graph.invoke(inputs, config=config)

    assert final_state["route"] == "CLARIFY"
    assert final_state["needs_clarification"] is True
    assert final_state["clarification_prompt"] is not None
