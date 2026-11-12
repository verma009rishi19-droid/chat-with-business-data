"""LangGraph Shared State Definition for Analytics Assistant."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.rag.retriever import RetrievedChunk


class ChartSpec(BaseModel):
    """Declarative JSON specification for Plotly rendering (no code execution)."""
    type: Literal["bar", "line", "pie", "scatter", "none"] = "none"
    title: str = ""
    x: str = ""
    y: str = ""
    labels: dict[str, str] = Field(default_factory=dict)
    data: list[dict[str, Any]] = Field(default_factory=list)


class AgentState(BaseModel):
    """Typed shared state container across all graph nodes."""
    # User input and routing
    question: str = ""
    route: Literal["SQL", "DOCS", "BOTH", "CLARIFY"] = "SQL"
    route_reasoning: str = ""

    # Human-in-the-loop clarification
    needs_clarification: bool = False
    clarification_prompt: str | None = None
    user_clarification: str | None = None

    # SQL Agent outputs
    sql_query: str | None = None
    sql_columns: list[str] = Field(default_factory=list)
    sql_rows: list[list[Any]] = Field(default_factory=list)
    sql_row_count: int = 0
    sql_error: str | None = None
    sql_execution_ms: float = 0.0

    # RAG Agent outputs
    retrieved_docs: list[RetrievedChunk] = Field(default_factory=list)
    retrieved_context: str = ""

    # Analyst & Chart outputs
    answer: str | None = None
    chart_spec: ChartSpec | None = None

    # Validation and self-correction loop
    is_valid: bool = False
    validation_error: str | None = None
    errors: list[str] = Field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 2

    # Tracing & Metadata
    trace_id: str | None = None
    thread_id: str | None = None
