"""Unit Tests for Router Node and Classification Logic."""

from __future__ import annotations

import pytest

from app.nodes.router import classify_question_heuristic


@pytest.mark.parametrize(
    "question,expected_route",
    [
        ("What was the total GMV in October 2025?", "SQL"),
        ("List top 5 selling products by quantity", "SQL"),
        ("What is the average delivery delay in Mumbai?", "SQL"),
        ("How many orders were cancelled?", "SQL"),
        ("What is the quick-commerce 15-minute delivery SLA policy?", "DOCS"),
        ("What is our corporate policy on customer refund matrix?", "DOCS"),
        ("What are the dark store operational guidelines?", "DOCS"),
        ("Which products had falling sales in Q3, and why?", "BOTH"),
        ("Why did delivery delays spike in Mumbai during July and August?", "BOTH"),
        ("Why did we run out of dry fruits and sweets in October?", "BOTH"),
        ("trends", "CLARIFY"),
        ("show data", "CLARIFY"),
        ("how are things?", "CLARIFY"),
    ],
)
def test_router_classification(question: str, expected_route: str):
    """Test heuristic and keyword routing across all four routes."""
    res = classify_question_heuristic(question)
    assert res.route == expected_route, f"Failed for '{question}': expected {expected_route}, got {res.route}"
