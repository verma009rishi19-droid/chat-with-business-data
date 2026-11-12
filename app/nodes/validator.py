"""Validator Node: Cross-checks SQL execution, numerical fidelity, and claim grounding."""

from __future__ import annotations

import logging
from typing import Any

from app.graph.state import AgentState

logger = logging.getLogger(__name__)


def validate_agent_execution(state: AgentState) -> tuple[bool, str | None]:
    """Validate that the pipeline executed safely, returned rows, and grounded numbers."""
    route = state.route

    # If route was CLARIFY, validation passes immediately
    if route == "CLARIFY" or state.needs_clarification:
        return True, None

    # Check 1: SQL Route Validation
    if route in ("SQL", "BOTH"):
        if state.sql_error:
            return False, f"SQL Error: {state.sql_error}"
        if not state.sql_query:
            return False, "SQL agent did not produce a query."
        if state.sql_rows is None:
            return False, "SQL execution produced no result set."

    # Check 2: DOCS Route Validation
    if route in ("DOCS", "BOTH"):
        if not state.retrieved_docs and not state.retrieved_context:
            logger.warning("No documents retrieved for DOCS route.")

    # Check 3: Answer Existence & Grounding
    if not state.answer or not state.answer.strip():
        return False, "Analyst failed to generate an answer."

    # Check 4: Citation Integrity
    if route in ("SQL", "BOTH") and state.sql_row_count > 0:
        if "[Table:" not in state.answer and "[Doc:" not in state.answer:
            logger.info("Validator notice: Missing explicit [Table:] or [Doc:] citation in answer.")

    # Check 5: Hallucination Sanity Check for Numbers
    # If SQL returned a single scalar (e.g. AOV or Count), verify number appears in text
    if state.sql_rows and len(state.sql_rows) == 1 and len(state.sql_columns) == 1:
        scalar_val = state.sql_rows[0][0]
        if isinstance(scalar_val, (int, float)):
            val_str = f"{scalar_val:.0f}"
            if len(val_str) > 2 and val_str not in state.answer.replace(",", ""):
                logger.warning("Scalar value %s not explicitly found in answer text.", val_str)

    return True, None


def validator_node(state: AgentState) -> dict:
    """LangGraph node execution for Validator."""
    is_valid, error_msg = validate_agent_execution(state)

    new_errors = list(state.errors)
    if error_msg:
        new_errors.append(error_msg)
        new_retry_count = state.retry_count + 1
        logger.warning(
            "Validation failed (Attempt %d/%d): %s",
            new_retry_count,
            state.max_retries,
            error_msg,
        )

        updates: dict[str, Any] = {
            "is_valid": False,
            "validation_error": error_msg,
            "errors": new_errors,
            "retry_count": new_retry_count,
        }

        # If exceeded max retries, provide graceful terminal message
        if new_retry_count >= state.max_retries:
            updates["answer"] = (
                f"### Analysis Incomplete\n"
                f"We were unable to complete the analysis after {state.max_retries} attempts due to: "
                f"`{error_msg}`.\n\n"
                f"Please try rephrasing your question or specifying exact metric and date filters."
            )
            updates["is_valid"] = True  # Allow termination
        return updates

    return {
        "is_valid": True,
        "validation_error": None,
        "errors": new_errors,
    }
