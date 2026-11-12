"""Router Node: Classifies incoming questions into SQL, DOCS, BOTH, or CLARIFY."""

from __future__ import annotations

import logging
from typing import Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.graph.state import AgentState
from app.llm.factory import get_llm

logger = logging.getLogger(__name__)

ROUTER_SYSTEM_PROMPT = """You are a senior query classification router for a Quick-Commerce analytics assistant.
Classify the user's question into exactly ONE of the four categories:

1. 'SQL':
   - Quantitative questions that can be answered purely by querying tabular data (aggregations, GMV, orders, revenue, delivery duration, ratings, counts, rankings).
   - Examples: "What was our total GMV in October?", "Top 5 dark stores by order volume", "Average delivery time in Mumbai".

2. 'DOCS':
   - Qualitative questions about company policy, standard operating procedures, supplier contracts, or operational guidelines that do not require executing a database query.
   - Examples: "What is our 15-minute delivery SLA policy?", "What compensation is given for delayed deliveries?", "What is the procedure for product recalls?".

3. 'BOTH':
   - Multi-faceted analytical questions that ask for quantitative data AND a qualitative root-cause explanation ("why", "cause", "reasons", "anomalies").
   - Examples: "Which products had falling sales in Q3 and why?", "Why did delivery times spike in July?", "Did milk sales increase after the May campaign and what drove it?".

4. 'CLARIFY':
   - Ambiguous, vague, or incomplete questions missing critical metrics or timeframes where a reasonable query cannot be formed without clarification.
   - Examples: "How are things looking?", "Show me the trend", "Can you fix the numbers?".
   - Provide a concise clarification question when choosing this route.
"""


class RouterOutput(BaseModel):
    route: Literal["SQL", "DOCS", "BOTH", "CLARIFY"] = Field(
        description="The assigned route: SQL, DOCS, BOTH, or CLARIFY."
    )
    reasoning: str = Field(description="Brief 1-sentence reasoning for this classification.")
    clarification_question: str | None = Field(
        default=None,
        description="Question to ask user if route is CLARIFY, otherwise null.",
    )


def classify_question_heuristic(question: str) -> RouterOutput:
    """Fast deterministic rule-based classifier used as fallback or offline testing."""
    q_lower = question.lower().strip()

    # Ambiguity check
    if len(q_lower.split()) < 3 or q_lower in ("how are things?", "show data", "show me trends", "trends", "numbers"):
        return RouterOutput(
            route="CLARIFY",
            reasoning="Question is ambiguous and lacks specific metrics or timeframes.",
            clarification_question="Could you please specify which metric (e.g., GMV, orders, delivery time) and timeframe you would like to analyze?",
        )

    has_why_keyword = any(k in q_lower for k in ["why", "cause", "reason", "explain", "drop in", "decline in"])
    has_data_keyword = any(
        k in q_lower
        for k in [
            "sales", "orders", "gmv", "revenue", "delay", "delivery", "stock",
            "volume", "top", "rate", "out of", "stockout", "product", "products",
            "items", "fruits", "sweets", "units"
        ]
    )
    has_policy_keyword = any(
        k in q_lower
        for k in [
            "policy", "sla", "procedure", "sop", "guideline", "guidelines",
            "rules", "compensation", "refund matrix", "campaign", "post-mortem",
            "post mortem", "notice", "memorandum", "retrospective"
        ]
    )
    has_metric_calc = any(k in q_lower for k in ["total", "average", "avg", "how many", "count", "sum", "highest", "lowest", "top", "rank"])

    if has_why_keyword and has_data_keyword:
        return RouterOutput(
            route="BOTH",
            reasoning="Question asks for data metrics and qualitative causal explanation ('why').",
        )
    if has_policy_keyword and not has_metric_calc:
        return RouterOutput(
            route="DOCS",
            reasoning="Question asks about policy, SLA, or guidelines without requesting a metric aggregation.",
        )
    if has_data_keyword:
        return RouterOutput(
            route="SQL",
            reasoning="Quantitative inquiry resolvable with relational database queries.",
        )

    return RouterOutput(
        route="SQL",
        reasoning="Default to SQL analysis.",
    )


def route_question(
    question: str,
    llm: BaseChatModel | None = None,
) -> RouterOutput:
    """Classify question with LLM structured output, falling back to heuristic on failure."""
    try:
        model = llm or get_llm(temperature=0.0)
        structured_llm = model.with_structured_output(RouterOutput)
        prompt = ChatPromptTemplate.from_messages([
            ("system", ROUTER_SYSTEM_PROMPT),
            ("human", "{question}"),
        ])
        chain = prompt | structured_llm
        result: RouterOutput = chain.invoke({"question": question})
        if isinstance(result, RouterOutput):
            return result
        # If result is dict
        if isinstance(result, dict):
            return RouterOutput(**result)
    except Exception as e:
        logger.warning("LLM structured classification failed: %s. Using heuristic router.", e)

    return classify_question_heuristic(question)


def router_node(state: AgentState, llm: BaseChatModel | None = None) -> dict:
    """LangGraph node implementation for routing."""
    # If user just provided clarification, combine it with original question
    active_question = state.question
    if state.user_clarification:
        active_question = f"{state.question} (Clarification: {state.user_clarification})"

    classification = route_question(active_question, llm=llm)

    updates = {
        "question": active_question,
        "route": classification.route,
        "route_reasoning": classification.reasoning,
        "needs_clarification": classification.route == "CLARIFY",
        "clarification_prompt": classification.clarification_question,
    }
    return updates
