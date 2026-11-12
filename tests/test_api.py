"""Integration Tests for FastAPI REST Endpoints (/health, /ask, /resume)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.routes import app
from app.config import settings
from app.rag.vector_store import ingest_knowledge_base


@pytest.fixture(scope="module", autouse=True)
def setup_api_test_env():
    """Ensure database and vector store are ready for API testing."""
    settings.DB_TYPE = "sqlite"
    ingest_knowledge_base(force_mock_embeddings=True)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client: TestClient):
    """Test GET /health returns system status and vector chunk counts."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "sqlite"
    assert data["db_connected"] is True
    assert data["vector_store_chunks"] >= 20


def test_ask_sql_endpoint(client: TestClient):
    """Test POST /ask for quantitative question returns SQL data and answer."""
    payload = {"question": "What is the total count of orders in the warehouse?"}
    response = client.post("/ask", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["route"] == "SQL"
    assert data["sql_query"] is not None
    assert data["sql_row_count"] > 0
    assert data["answer"] is not None
    assert data["thread_id"] is not None
    assert data["execution_ms"] > 0


def test_ask_docs_endpoint(client: TestClient):
    """Test POST /ask for qualitative question returns citations."""
    payload = {"question": "What is our corporate 15-minute delivery SLA policy?"}
    response = client.post("/ask", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["route"] == "DOCS"
    assert len(data["sources"]) > 0
    assert any("sla" in s["source"].lower() or "policy" in s["source"].lower() for s in data["sources"])


def test_ask_both_endpoint(client: TestClient):
    """Test POST /ask for multi-agent analytical 'why' question."""
    payload = {"question": "Which sourdough products had falling sales in Q3 and why?"}
    response = client.post("/ask", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["route"] == "BOTH"
    assert data["sql_query"] is not None
    assert len(data["sources"]) > 0
    assert data["answer"] is not None


def test_ask_clarify_endpoint(client: TestClient):
    """Test POST /ask with ambiguous question triggers human-in-the-loop clarification."""
    payload = {"question": "trends"}
    response = client.post("/ask", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["route"] == "CLARIFY"
    assert data["needs_clarification"] is True
    assert data["clarification_prompt"] is not None
    assert data["thread_id"] is not None


def test_resume_endpoint(client: TestClient):
    """Test POST /resume completes workflow after user clarification."""
    # First invoke ambiguous question to get thread_id
    init_res = client.post("/ask", json={"question": "trends"})
    thread_id = init_res.json()["thread_id"]

    # Now resume with clarification
    resume_payload = {
        "thread_id": thread_id,
        "user_clarification": "Focus on total orders in October 2025 during festive Diwali.",
    }
    resume_res = client.post("/resume", json=resume_payload)
    assert resume_res.status_code == 200
    data = resume_res.json()

    assert data["needs_clarification"] is False
    assert data["answer"] is not None


def test_validation_error_on_empty_question(client: TestClient):
    """Test input validation rejects empty question with 422 status."""
    response = client.post("/ask", json={"question": ""})
    assert response.status_code == 422
