"""Pydantic Request and Response Schemas for FastAPI Endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.graph.state import ChartSpec


class AskRequest(BaseModel):
    """Payload to submit a business question."""
    question: str = Field(
        ...,
        min_length=1,
        description="Business question in plain English",
        json_schema_extra={"example": "Which products had falling sales in Q3, and why?"},
    )
    thread_id: str | None = Field(default=None, description="Optional existing session/thread ID for conversational state persistence")


class ResumeRequest(BaseModel):
    """Payload to resume an interrupted workflow after human clarification."""
    thread_id: str = Field(..., min_length=1, description="Thread ID of the paused clarification state")
    user_clarification: str = Field(
        ...,
        min_length=1,
        description="User's clarification response",
        json_schema_extra={"example": "Focus on Artisanal Sourdough loaves in Mumbai."},
    )


class DocSourceResponse(BaseModel):
    """Retrieved document reference footnote."""
    doc_id: str = "UNKNOWN"
    title: str = ""
    source: str = ""
    section: str = ""
    score: float = 0.0


class AskResponse(BaseModel):
    """Standardized API response for business analytics questions."""
    answer: str
    route: str
    chart_spec: ChartSpec | None = None
    sql_query: str | None = None
    sql_columns: list[str] = Field(default_factory=list)
    sql_row_count: int = 0
    sources: list[DocSourceResponse] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification_prompt: str | None = None
    thread_id: str
    trace_id: str | None = None
    execution_ms: float = 0.0


class HealthResponse(BaseModel):
    """System and dependency health status."""
    status: str
    version: str = "0.1.0"
    database: str
    db_connected: bool
    vector_store_chunks: int
