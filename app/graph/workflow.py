"""Full LangGraph Orchestration Workflow with Conditional Routing, Retries, and Human-in-the-Loop."""

from __future__ import annotations

import logging
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.graph.state import AgentState
from app.nodes.analyst import analyst_node
from app.nodes.clarifier import clarifier_node
from app.nodes.rag_agent import rag_agent_node
from app.nodes.router import router_node
from app.nodes.sql_agent import sql_agent_node
from app.nodes.validator import validator_node

logger = logging.getLogger(__name__)


def route_decision(state: AgentState) -> str:
    """Conditional edge decision function following router classification."""
    route = state.route
    if route == "CLARIFY":
        return "clarifier"
    if route == "DOCS":
        return "rag_agent"
    return "sql_agent"  # Both SQL and BOTH start at sql_agent


def clarifier_decision(state: AgentState) -> str:
    """Conditional edge decision after clarification node."""
    if state.needs_clarification:
        return END
    # If clarification was provided, loop back to router
    return "router"


def sql_post_decision(state: AgentState) -> str:
    """Conditional edge after sql_agent."""
    if state.route == "BOTH":
        return "rag_agent"
    return "analyst"


def validator_decision(state: AgentState) -> str:
    """Conditional edge for validation and retry loop."""
    if state.is_valid:
        return END

    if state.retry_count < state.max_retries:
        logger.info("Validation retry triggered (Attempt %d/%d)", state.retry_count, state.max_retries)
        if state.route in ("SQL", "BOTH"):
            return "sql_agent"
        return "analyst"

    return END


def create_analytics_graph(checkpointer: Any | None = None) -> Any:
    """Build and compile the multi-agent LangGraph workflow."""
    workflow = StateGraph(AgentState)

    # 1. Add Nodes
    workflow.add_node("router", router_node)
    workflow.add_node("clarifier", clarifier_node)
    workflow.add_node("sql_agent", sql_agent_node)
    workflow.add_node("rag_agent", rag_agent_node)
    workflow.add_node("analyst", analyst_node)
    workflow.add_node("validator", validator_node)

    # 2. Add Edges
    workflow.add_edge(START, "router")

    # Conditional Routing from Router
    workflow.add_conditional_edges(
        "router",
        route_decision,
        {
            "clarifier": "clarifier",
            "sql_agent": "sql_agent",
            "rag_agent": "rag_agent",
        },
    )

    # Clarifier conditional branch
    workflow.add_conditional_edges(
        "clarifier",
        clarifier_decision,
        {
            "router": "router",
            END: END,
        },
    )

    # SQL Agent branch (route to RAG if BOTH, else Analyst)
    workflow.add_conditional_edges(
        "sql_agent",
        sql_post_decision,
        {
            "rag_agent": "rag_agent",
            "analyst": "analyst",
        },
    )

    # RAG Agent proceeds to Analyst
    workflow.add_edge("rag_agent", "analyst")

    # Analyst proceeds to Validator
    workflow.add_edge("analyst", "validator")

    # Validator conditional branch (Retry or End)
    workflow.add_conditional_edges(
        "validator",
        validator_decision,
        {
            "sql_agent": "sql_agent",
            "analyst": "analyst",
            END: END,
        },
    )

    # Default to MemorySaver checkpointer for state checkpointing and interrupt resumption
    saver = checkpointer if checkpointer is not None else MemorySaver()
    compiled_graph = workflow.compile(checkpointer=saver)
    return compiled_graph


# Pre-compiled application graph instance
app_graph = create_analytics_graph()
