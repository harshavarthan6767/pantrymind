"""
Meal Planning Tool for PantryMind — PuLP Linear Programming.

Solves a cost-minimisation meal plan subject to calorie, protein, variety,
and inventory constraints.
"""

import logging

from google.adk.tools import ToolContext

logger = logging.getLogger("pantrymind.tools.meal_planner")

# PuLP is imported lazily inside the function to let the module load
# even when PuLP is not installed (graceful degradation).


async def solve_meal_plan(
    inventory: list[dict],
    target_daily_calories: int,
    days: int = 7,
    strict_inventory: bool = True,
    tool_context: ToolContext = None,
) -> dict:
    """Generate an optimal meal plan using linear programming (PuLP).

    Call this tool when the user asks for a meal plan, weekly food plan,
    or wants to optimise their grocery usage. The solver minimises total
    cost while meeting calorie and protein targets and enforcing variety.

    Args:
        inventory: List of dicts, each with keys:
            - name (str): item name
            - quantity_kg (float): available quantity in kg
            - cost_per_kg (float): price per kg in INR
            - calories_per_kg (float): kcal per kg
            - protein_per_kg (float): grams protein per kg
        target_daily_calories: Target kcal per day (e.g. 2000).
        days: Number of days to plan for (default 7).
        strict_inventory: If True, quantities are capped at current stock.
            If False, extra items are added to a shopping list.
        tool_context: ADK tool context.

    Returns:
        dict with keys:
            - status: 'optimal' | 'infeasible' | 'error'
            - plan: dict mapping item name → quantity_kg to use
            - shopping_list: list of dicts (only when strict_inventory=False)
            - macros_summary: {total_calories, total_protein_g, total_cost}
            - days: number of days planned
    """
    try:
        import pulp
    except ImportError:
        logger.error("PuLP is not installed. Run: pip install pulp")
        return {
            "status": "error",
            "error": "PuLP library not installed. Cannot solve meal plan.",
        }

    try:
        if not inventory:
            return {"status": "error", "error": "Inventory is empty. Cannot plan meals."}

        total_cal_target = target_daily_calories * days
        total_protein_target = 50.0 * days  # 50 g/day minimum
        total_max_any_item = 0.30  # No single item > 30 % of total weight

        # ── Decision variables ─────────────────────────────────────────
        # x_i = kg of item i to include in the plan
        items = {item["name"]: item for item in inventory}
        x = {}
        for name, item in items.items():
            upper = item["quantity_kg"] if strict_inventory else None
            x[name] = pulp.LpVariable(
                f"x_{name.replace(' ', '_')}",
                lowBound=0,
                upBound=upper,
                cat="Continuous",
            )

        # ── Problem ────────────────────────────────────────────────────
        prob = pulp.LpProblem("MealPlan", pulp.LpMinimize)

        # Objective: minimise total cost
        prob += pulp.lpSum(
            x[n] * items[n]["cost_per_kg"] for n in items
        ), "TotalCost"

        # Constraint 1: meet calorie target
        prob += (
            pulp.lpSum(x[n] * items[n]["calories_per_kg"] for n in items)
            >= total_cal_target,
            "CalorieTarget",
        )

        # Constraint 2: meet protein target
        prob += (
            pulp.lpSum(x[n] * items[n]["protein_per_kg"] for n in items)
            >= total_protein_target,
            "ProteinTarget",
        )

        # Constraint 3: variety — no single item > 30 % of total weight
        total_weight = pulp.lpSum(x[n] for n in items)
        for name in items:
            prob += (
                x[name] <= total_max_any_item * total_weight,
                f"Variety_{name.replace(' ', '_')}",
            )

        # ── Solve ──────────────────────────────────────────────────────
        solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=30)
        prob.solve(solver)

        status = pulp.LpStatus[prob.status]
        logger.info("LP solver status: %s", status)

        if status != "Optimal":
            return {
                "status": "infeasible",
                "message": (
                    "Could not find an optimal plan. Try relaxing constraints, "
                    "adding more inventory, or reducing target calories."
                ),
            }

        # ── Extract solution ───────────────────────────────────────────
        plan: dict[str, float] = {}
        shopping_list: list[dict] = []
        total_cost = 0.0
        total_cal = 0.0
        total_protein = 0.0

        for name, var in x.items():
            qty = round(var.varValue or 0.0, 3)
            if qty <= 0:
                continue
            plan[name] = qty
            item = items[name]
            total_cost += qty * item["cost_per_kg"]
            total_cal += qty * item["calories_per_kg"]
            total_protein += qty * item["protein_per_kg"]

            # Shopping list: items that exceed current stock
            if not strict_inventory:
                available = item.get("quantity_kg", 0)
                if qty > available:
                    shopping_list.append({
                        "name": name,
                        "need_kg": round(qty - available, 3),
                        "estimated_cost": round(
                            (qty - available) * item["cost_per_kg"], 2
                        ),
                    })

        result = {
            "status": "optimal",
            "plan": plan,
            "macros_summary": {
                "total_calories": round(total_cal, 0),
                "total_protein_g": round(total_protein, 1),
                "total_cost_inr": round(total_cost, 2),
                "daily_avg_calories": round(total_cal / days, 0),
                "daily_avg_protein_g": round(total_protein / days, 1),
            },
            "days": days,
        }

        if not strict_inventory and shopping_list:
            result["shopping_list"] = shopping_list

        logger.info(
            "Meal plan solved: %d items, %.0f kcal, ₹%.0f total",
            len(plan), total_cal, total_cost,
        )
        return result

    except Exception as e:
        logger.error("Meal plan solver failed: %s", e, exc_info=True)
        return {"status": "error", "error": str(e)}
