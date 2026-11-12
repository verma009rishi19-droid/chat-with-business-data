"""FastAPI Application Server for Multi-Agent Business Analytics."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from langgraph.errors import GraphInterrupt
from langgraph.types import Command

from app.api.models import AskRequest, AskResponse, DocSourceResponse, HealthResponse, ResumeRequest
from app.config import settings
from app.db.connection import check_database_health
from app.graph.workflow import app_graph
from app.observability import get_tracing_callbacks
from app.rag.vector_store import get_or_create_collection

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle management."""
    logger.info("Initializing 'Chat with Your Business Data' API service...")
    # Verify DB connectivity on startup
    db_health = check_database_health()
    logger.info("Database connectivity check: %s", db_health["status"])
    yield
    logger.info("Shutting down API service.")


app = FastAPI(
    title="Chat with Your Business Data API",
    description="Multi-agent analytics assistant integrating Text-to-SQL, RAG, and safe chart generation.",
    version="0.1.0",
    lifespan=lifespan,
)

# Enable CORS for Streamlit UI or web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    """System health check and dependency connectivity verification."""
    db_status = check_database_health()
    vector_count = 0
    try:
        col = get_or_create_collection()
        vector_count = col.count()
    except Exception as e:
        logger.warning("Could not read vector store count: %s", e)

    return HealthResponse(
        status="healthy" if db_status.get("connected") else "degraded",
        database=settings.DB_TYPE,
        db_connected=bool(db_status.get("connected")),
        vector_store_chunks=vector_count,
    )


@app.post("/ask", response_model=AskResponse, tags=["Analytics"])
async def ask_question(request: AskRequest) -> AskResponse:
    """Submit a business question to the multi-agent graph."""
    start_time = time.perf_counter()
    thread_id = request.thread_id or f"sess_{uuid.uuid4().hex[:12]}"
    trace_id = f"tr_{uuid.uuid4().hex[:8]}"
    callbacks = get_tracing_callbacks(trace_id=trace_id, tags=["api", "ask"])
    config = {
        "configurable": {"thread_id": thread_id},
        "callbacks": callbacks,
    }

    initial_inputs = {
        "question": request.question.strip(),
        "thread_id": thread_id,
        "trace_id": trace_id,
    }

    try:
        final_state = app_graph.invoke(initial_inputs, config=config)
    except GraphInterrupt:
        logger.info("Graph interrupted for human clarification on thread %s", thread_id)
        state_snap = app_graph.get_state(config)
        snap_values = state_snap.values
        prompt = snap_values.get("clarification_prompt") or "Please clarify what timeframe or metric you would like to analyze."
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return AskResponse(
            answer=f"**Clarification Needed:** {prompt}",
            route="CLARIFY",
            needs_clarification=True,
            clarification_prompt=prompt,
            thread_id=thread_id,
            trace_id=initial_inputs.get("trace_id"),
            execution_ms=duration_ms,
        )
    except Exception as e:
        logger.error("Graph execution failure: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while executing the analytics graph: {e!s}",
        )

    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # Check if graph halted on interrupt or requested clarification
    if final_state.get("__interrupt__") or final_state.get("needs_clarification"):
        prompt = final_state.get("clarification_prompt") or "Please clarify what timeframe or metric you would like to analyze."
        return AskResponse(
            answer=f"**Clarification Needed:** {prompt}",
            route="CLARIFY",
            needs_clarification=True,
            clarification_prompt=prompt,
            thread_id=thread_id,
            trace_id=initial_inputs.get("trace_id"),
            execution_ms=duration_ms,
        )

    # Convert retrieved chunks into API response sources
    sources = []
    if final_state.get("retrieved_docs"):
        for doc in final_state["retrieved_docs"]:
            sources.append(
                DocSourceResponse(
                    doc_id=getattr(doc, "doc_id", "UNKNOWN"),
                    title=getattr(doc, "title", "Business Document"),
                    source=getattr(doc, "source", "unknown.md"),
                    section=getattr(doc, "section", "General"),
                    score=getattr(doc, "score", 0.0),
                )
            )

    return AskResponse(
        answer=final_state.get("answer") or "No answer could be determined.",
        route=final_state.get("route", "SQL"),
        chart_spec=final_state.get("chart_spec"),
        sql_query=final_state.get("sql_query"),
        sql_columns=final_state.get("sql_columns", []),
        sql_row_count=final_state.get("sql_row_count", 0),
        sources=sources,
        needs_clarification=final_state.get("needs_clarification", False),
        clarification_prompt=final_state.get("clarification_prompt"),
        thread_id=thread_id,
        trace_id=final_state.get("trace_id"),
        execution_ms=duration_ms,
    )


@app.post("/resume", response_model=AskResponse, tags=["Analytics"])
async def resume_clarification(request: ResumeRequest) -> AskResponse:
    """Resume an interrupted graph execution with user-provided clarification."""
    start_time = time.perf_counter()
    trace_id = f"tr_{uuid.uuid4().hex[:8]}"
    callbacks = get_tracing_callbacks(trace_id=trace_id, tags=["api", "resume"])
    config = {
        "configurable": {"thread_id": request.thread_id},
        "callbacks": callbacks,
    }

    try:
        # Resume graph execution using LangGraph Command
        resume_payload = Command(resume=request.user_clarification.strip())
        final_state = app_graph.invoke(resume_payload, config=config)
    except Exception as e:
        logger.info("Direct Command resume fell back to state update: %s", e)
        # Fallback: update state directly and resume
        resume_state = {
            "user_clarification": request.user_clarification.strip(),
            "needs_clarification": False,
        }
        final_state = app_graph.invoke(resume_state, config=config)

    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

    sources = []
    if final_state.get("retrieved_docs"):
        for doc in final_state["retrieved_docs"]:
            sources.append(
                DocSourceResponse(
                    doc_id=getattr(doc, "doc_id", "UNKNOWN"),
                    title=getattr(doc, "title", "Business Document"),
                    source=getattr(doc, "source", "unknown.md"),
                    section=getattr(doc, "section", "General"),
                    score=getattr(doc, "score", 0.0),
                )
            )

    return AskResponse(
        answer=final_state.get("answer") or "No answer could be determined.",
        route=final_state.get("route", "SQL"),
        chart_spec=final_state.get("chart_spec"),
        sql_query=final_state.get("sql_query"),
        sql_columns=final_state.get("sql_columns", []),
        sql_row_count=final_state.get("sql_row_count", 0),
        sources=sources,
        needs_clarification=final_state.get("needs_clarification", False),
        clarification_prompt=final_state.get("clarification_prompt"),
        thread_id=request.thread_id,
        trace_id=final_state.get("trace_id"),
        execution_ms=duration_ms,
    )
