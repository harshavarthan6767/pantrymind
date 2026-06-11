"""
evaluation/scenarios.py — Phase 3 · Day 3
==========================================
Defines the 5 canonical evaluation scenarios for PantryMind's hackathon submission.

Each scenario is a self-contained test case that:
  1. Sends a user message to the running server's SSE endpoint
  2. Collects the full streaming response
  3. Passes it to the rubric evaluator
"""

from dataclasses import dataclass, field
from typing import Callable, Any


@dataclass
class EvalScenario:
    id: str
    name: str
    description: str
    user_message: str
    # Expected substrings / assertions in the response (at least one must pass)
    expected_keywords: list[str]
    # The domain(s) this tests
    domains: list[str]
    # Whether the scenario is expected to trigger an approval gate
    expects_approval: bool = False
    # Additional setup callable (async) — e.g., seed a specific inventory state
    setup: Callable | None = None


# ─── The 5 Scenarios ─────────────────────────────────────────────────────────

SCENARIOS: list[EvalScenario] = [

    EvalScenario(
        id="S1_PANTRY_SEMANTIC",
        name="Semantic Pantry Query",
        description="Tests Vector Search — asks for ingredients suitable for a Thai curry.",
        user_message="What ingredients do I have that would work in a Thai curry?",
        expected_keywords=["coconut", "lemon", "chilli", "chicken", "rice", "ginger",
                           "sorry", "don't have", "nothing"],
        domains=["pantry", "vector_search"],
        expects_approval=False
    ),

    EvalScenario(
        id="S2_MEAL_PLAN",
        name="Meal Plan With Expiry Priority",
        description="Tests kitchen agent — generates a meal plan prioritizing expiring items.",
        user_message="Generate a healthy dinner plan for tonight using items that are about to expire.",
        expected_keywords=["expires", "expiring", "kcal", "protein", "recipe", "dinner",
                           "ingredients", "grams", "steps"],
        domains=["kitchen", "reflexion"],
        expects_approval=False
    ),

    EvalScenario(
        id="S3_RECEIPT_SCAN",
        name="Receipt Scan With Approval Gate",
        description="Tests governed receipt ingestion — agent should create a pending action instead of directly inserting.",
        user_message="I just bought groceries — scan receipt and add everything to my pantry.",
        expected_keywords=["approval", "pending", "confirm", "added", "items"],
        domains=["receipt", "governance"],
        expects_approval=True
    ),

    EvalScenario(
        id="S4_BUDGET_ANALYSIS",
        name="Finance Budget Analysis",
        description="Tests finance agent — asks how much was spent this month.",
        user_message="How much have I spent on groceries this month? Am I on track with my budget?",
        expected_keywords=["₹", "spent", "budget", "month", "remaining", "total", "groceries"],
        domains=["finance"],
        expects_approval=False
    ),

    EvalScenario(
        id="S5_SHOPPING_LIST",
        name="Smart Shopping List Generation",
        description="Tests shopping agent — generates a prioritized shopping list within budget.",
        user_message="Generate my shopping list for this week. Keep it under ₹2000.",
        expected_keywords=["₹", "shopping", "priority", "buy", "list", "total"],
        domains=["shopping"],
        expects_approval=False
    ),
]

# Lookup by ID
SCENARIO_MAP = {s.id: s for s in SCENARIOS}
