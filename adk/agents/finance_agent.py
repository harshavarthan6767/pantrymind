import os
from google.adk.agents import LlmAgent
from adk.tools.fast_db_tools import get_finance_overview
from adk.tools.finance_tools import (
    parse_date_range,          # converts natural lang dates to ISO
    compute_budget_summary,    # salary - spent = disposable
    compare_period_totals,     # month-over-month delta
)
from adk.patterns.reflexion import apply_reflexion
from google.adk.tools import FunctionTool

def validate_finance_response(user_query: str, draft_response: str) -> str:
    """
    Validates the finance response for correct currency, date ranges, and
    mathematical accuracy before returning to the user.
    """
    return apply_reflexion(
        user_query=user_query,
        draft_response=draft_response,
        domain="finance",
        model_name=os.getenv("FINANCE_MODEL", "gemini-3.1-flash-lite")
    )

FINANCE_SYSTEM_PROMPT = """
You are the PantryMind Finance Analyst. You answer spending questions using the
financial_ledger collection.

## COLLECTION: financial_ledger
Fields: type ("expense"/"income"), amount, category, date (ISODate), 
        description, receipt_id

## FAST QUERY TOOL
Use get_finance_overview(user_id="<provided_user_id>", start_date=<iso>, end_date=<iso>)
for spend totals, category breakdowns, and recent transactions.

## RULES
- Always call parse_date_range() first to convert natural language to ISO dates
- Always pass the provided user_id into get_finance_overview()
- Use ₹ (INR) for amounts unless data shows otherwise
- Keep answers to 2-3 sentences with the key number up front
- Never guess at amounts — always query first

## MANDATORY VALIDATION
After constructing your answer:
  1. Call validate_finance_response(user_query=<question>, draft_response=<your answer>)
  2. Return whatever it returns.

This ensures amounts are in ₹, date ranges are explicit, and numbers are accurate.
"""

def create_finance_agent() -> LlmAgent:
    return LlmAgent(
        name="finance_agent",
        model=os.getenv("FINANCE_MODEL", "gemini-3.1-pro"),
        description="Tracks household budget, spending analytics, and purchase ledger.",
        instruction=FINANCE_SYSTEM_PROMPT,
        tools=[
            FunctionTool(get_finance_overview),
            FunctionTool(parse_date_range),
            FunctionTool(compute_budget_summary),
            FunctionTool(compare_period_totals),
            FunctionTool(validate_finance_response),
        ]
    )
