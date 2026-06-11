QUERY_TYPE_TO_MODEL = {
    # Finance: simple, structured, high-volume → Flash Lite
    "finance_query":       "gemini-3.1-flash-lite",
    "ledger_lookup":       "gemini-3.1-flash-lite",
    "budget_calculation":  "gemini-3.1-flash-lite",
    "expense_summary":     "gemini-3.1-flash-lite",

    # Pantry + Receipt: vision + structured output → Flash
    "receipt_scan":        "gemini-3.1-flash",
    "pantry_management":   "gemini-3.1-pro",

    # Kitchen: multi-step agentic, complex reasoning → Pro
    "meal_planning":       "gemini-3.1-pro-preview",
    "recipe_generation":   "gemini-3.1-pro-preview",
}

def get_model_for_task(task_type: str) -> str:
    return QUERY_TYPE_TO_MODEL.get(task_type, "gemini-3.1-pro")
