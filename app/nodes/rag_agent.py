"""RAG Agent Node for retrieving relevant business documents."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from app.rag.retriever import RetrievedChunk, format_chunks_for_analyst, retrieve_relevant_chunks

logger = logging.getLogger(__name__)


class RAGAgentResult(BaseModel):
    docs: list[RetrievedChunk] = Field(default_factory=list)
    formatted_context: str = ""
    doc_count: int = 0


def run_rag_agent(
    question: str,
    top_k: int = 3,
    score_threshold: float = 0.20,
    force_mock_embeddings: bool = False,
) -> RAGAgentResult:
    """Execute RAG retrieval pipeline for a given business question."""
    chunks = retrieve_relevant_chunks(
        query=question,
        top_k=top_k,
        score_threshold=score_threshold,
        force_mock_embeddings=force_mock_embeddings,
    )
    formatted = format_chunks_for_analyst(chunks)
    return RAGAgentResult(
        docs=chunks,
        formatted_context=formatted,
        doc_count=len(chunks),
    )


def rag_agent_node(state: Any, force_mock_embeddings: bool = False) -> dict:
    """LangGraph node execution for RAG Agent."""
    question = getattr(state, "question", "") if not isinstance(state, dict) else state.get("question", "")
    result = run_rag_agent(question=question, force_mock_embeddings=force_mock_embeddings)

    return {
        "retrieved_docs": result.docs,
        "retrieved_context": result.formatted_context,
    }

