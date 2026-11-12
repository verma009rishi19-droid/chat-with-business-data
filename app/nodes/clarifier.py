"""Clarifier Node: Human-in-the-Loop Interruption and State Resumption."""

from __future__ import annotations

import logging

from langgraph.types import interrupt

from app.graph.state import AgentState

logger = logging.getLogger(__name__)


def clarifier_node(state: AgentState) -> dict:
    """Pause graph execution to request human clarification using LangGraph Checkpointing."""
    # If user already provided clarification in the payload directly
    if state.user_clarification:
        logger.info("Resuming with user clarification: %s", state.user_clarification)
        merged_q = f"{state.question} [User clarified: {state.user_clarification}]"
        return {
            "question": merged_q,
            "needs_clarification": False,
            "clarification_prompt": None,
        }

    prompt = state.clarification_prompt or (
        "Your question appears ambiguous or is missing a specific metric or timeframe. "
        "Could you please clarify what specific data or period you are looking for?"
    )

    logger.info("Triggering human-in-the-loop interrupt with prompt: %s", prompt)
    
    # Interrupt execution and wait for Command(resume=...)
    human_input = interrupt({
        "type": "clarification_needed",
        "prompt": prompt,
        "original_question": state.question,
    })

    user_text = str(human_input).strip()
    logger.info("Resumed from interrupt with input: %s", user_text)
    merged_q = f"{state.question} [User clarified: {user_text}]"
    return {
        "question": merged_q,
        "user_clarification": user_text,
        "needs_clarification": False,
        "clarification_prompt": None,
    }
