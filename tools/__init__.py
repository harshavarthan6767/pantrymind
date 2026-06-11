"""
PantryMind Tools Package.

Exports all tool functions so they can be registered as Google ADK
FunctionTools in the agent definitions.

Usage:
    from tools import parse_receipt_image, compute_indian_tax, ...
    # or
    from tools import ALL_TOOLS  # flat list of all tool functions
"""

# ── OCR Tools ──────────────────────────────────────────────────────────────
# 🚀 Storage Tools ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Storage tools removed as part of cleanup

# ── Tax Tools ──────────────────────────────────────────────────────────────
from tools.tax_tools import (
    compute_indian_tax,
    compute_disposable_income,
)

# ── Meal Planner ───────────────────────────────────────────────────────────
from tools.meal_planner import (
    solve_meal_plan,
)

# ── Expiry Tools ───────────────────────────────────────────────────────────
from tools.expiry_tools import (
    lookup_shelf_life,
    calculate_expiry,
    calculate_suggested_usage,
    get_expiring_soon,
)

# ── Warranty Tools ─────────────────────────────────────────────────────────
from tools.warranty_tools import (
    add_warranty,
    get_expiring_warranties,
    get_warranty_by_item,
    mark_warranty_alerted,
)

# ── Behavior Insight Tools ─────────────────────────────────────────────────
from tools.behavior_tools import (
    generate_weekly_snapshot,
    get_spending_by_day_of_week,
    get_category_trend,
    get_top_merchants,
    generate_insights_report,
)

# ── Carbon Footprint Tools ─────────────────────────────────────────────────
from tools.carbon_tools import (
    lookup_carbon_footprint,
    log_carbon_impact,
    get_carbon_summary,
    suggest_green_swaps,
)

# ── Nutrition Tools ────────────────────────────────────────────────────────
from tools.nutrition_tools import (
    lookup_nutrition,
    log_nutrition_intake,
    get_weekly_nutrition,
    check_deficiencies,
    generate_nutrition_report,
)

# ── Restock Tools ──────────────────────────────────────────────────────────
from tools.restock_tools import (
    calculate_consumption_rate,
    predict_depletion,
    update_restock_prediction,
    get_restock_alerts,
    generate_shopping_list,
)


# 🚀 Master list for bulk registration ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ALL_TOOLS = [
    # Tax
    compute_indian_tax,
    compute_disposable_income,
    # Meal planning
    solve_meal_plan,
    # Expiry
    lookup_shelf_life,
    calculate_expiry,
    calculate_suggested_usage,
    get_expiring_soon,
    # Warranty
    add_warranty,
    get_expiring_warranties,
    get_warranty_by_item,
    mark_warranty_alerted,
    # Behavior
    generate_weekly_snapshot,
    get_spending_by_day_of_week,
    get_category_trend,
    get_top_merchants,
    generate_insights_report,
    # Carbon
    lookup_carbon_footprint,
    log_carbon_impact,
    get_carbon_summary,
    suggest_green_swaps,
    # Nutrition
    lookup_nutrition,
    log_nutrition_intake,
    get_weekly_nutrition,
    check_deficiencies,
    generate_nutrition_report,
    # Restock
    calculate_consumption_rate,
    predict_depletion,
    update_restock_prediction,
    get_restock_alerts,
    generate_shopping_list,
]

__all__ = [fn.__name__ for fn in ALL_TOOLS] + ["ALL_TOOLS"]
