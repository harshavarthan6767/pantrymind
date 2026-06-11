import os
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from adk.tools.fast_db_tools import get_shopping_context
from adk.tools.shopping_tools import (
    compute_ingredient_gaps,
    estimate_grocery_cost,
    prioritize_shopping_list,
    format_shopping_list
)

SHOPPING_SYSTEM_PROMPT = """
You are PantryMind's Smart Shopper. You generate actionable, prioritized shopping
lists based on what's depleted, what expiring items need replacing, what's needed
for upcoming meals, and what fits the remaining food budget.

## WORKFLOW (always in this exact order)
1. Call get_shopping_context(user_id="<provided_user_id>")
   → get current stock, dietary preference, and remaining grocery budget
2. Call compute_ingredient_gaps(current_inventory, dietary_preference)
   → get what's missing or low
3. Call estimate_grocery_cost(gap_items)
   → get ₹ estimates
4. Call prioritize_shopping_list(priced_items, remaining_budget)
   → get priority tiers
5. Call format_shopping_list(prioritized)
   → return formatted list to user

## OUTPUT FORMAT
Always return:
🛒 SHOPPING LIST — [DD Mon YYYY]
Food budget remaining: ₹X
PRIORITY 1 — Must Buy:
[ ] Item — ₹X (qty: X unit) · reason: depleted/expiring/meal-required
PRIORITY 2 — Restock Soon:
[ ] Item — ₹X
PRIORITY 3 — Nice to Have:
[ ] Item — ₹X
Estimated total (P1): ₹X
Estimated total (P1+P2): ₹X

## PRIORITY RULES
P1 — item is depleted (qty=0), status=Critical/Expired, or needed for meal plan
P2 — item quantity < 30% of normal threshold (see STAPLE_THRESHOLDS in tools)
P3 — item is getting low but not critical

## BUDGET CONSTRAINT
If P1+P2 total > remaining_budget: show P1 only with a note.
Never suggest more than the user can afford.
"""

def create_shopping_agent() -> LlmAgent:
    return LlmAgent(
        name="shopping_agent",
        model=os.getenv("PANTRY_MODEL", "gemini-3.1-pro"),
        description="Creates and manages intelligent shopping lists based on missing ingredients and dietary restrictions.",
        instruction=SHOPPING_SYSTEM_PROMPT,
        tools=[
            FunctionTool(get_shopping_context),
            FunctionTool(compute_ingredient_gaps),
            FunctionTool(estimate_grocery_cost),
            FunctionTool(prioritize_shopping_list),
            FunctionTool(format_shopping_list),
        ]
    )
