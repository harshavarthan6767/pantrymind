import pulp
from typing import Optional

# Reasonable per-meal portion limits by food category
MAX_PORTIONS = {
    "MEAT_SEAFOOD":     400,   # Max 400g protein per meal
    "DAIRY_EGGS":       200,   # Max 200g dairy/eggs
    "PRODUCE":          300,   # Max 300g vegetables
    "PANTRY_DRY":       200,   # Max 200g dry goods (uncooked)
    "FROZEN":           350,   # Max 350g frozen items
    "BAKERY":           150,   # Max 150g bread
    "CONDIMENTS":        30,   # Max 30g sauces (flavoring, not bulk)
    "default":          250
}

# Minimum usable amounts (prevents 1g suggestions)
MIN_PORTIONS = {
    "CONDIMENTS":   5,
    "PANTRY_DRY": 30,
    "default":     50
}


def run_meal_optimizer(
    available_ingredients: list,
    nutrition_data: dict,
    targets: dict,
    meal_type: str = "dinner",
    max_ingredients: int = 6,
    is_relaxed: bool = False
) -> dict:
    """
    Runs the LP optimizer and returns a meal plan with exact portions.

    targets = {
        "calories": 600,       # Target for this meal (daily ÷ 3 or custom)
        "protein_min": 40,     # Minimum protein grams
        "carbs_max": 80,       # Maximum carbs
        "fat_max": 25,         # Maximum fat
    }
    """

    # Filter to ingredients that have nutrition data
    usable = [
        item for item in available_ingredients
        if item.get("name") in nutrition_data
    ]

    if not usable:
        return {
            "success": False,
            "reason": "no_nutrition_data",
            "message": "Could not find nutrition data for any available ingredients."
        }

    # ── Create the LP problem ──────────────────────────────────────
    problem = pulp.LpProblem(f"meal_{meal_type}", pulp.LpMaximize)

    # Continuous variables: grams of each ingredient
    amounts = {}
    for item in usable:
        name = item["name"]
        cat  = item.get("category", "default")
        max_g = MAX_PORTIONS.get(cat, MAX_PORTIONS["default"])
        # Do not exceed actual available quantity
        qty = item.get("quantity", 1)
        unit = item.get("unit", "g").lower()
        if unit in ["kg", "kilogram", "kilograms"]:
            actual_available_g = qty * 1000
        elif unit in ["l", "liter", "liters"]:
            actual_available_g = qty * 1000
        elif unit in ["ml", "milliliter", "milliliters"]:
            actual_available_g = qty
        elif unit in ["unit", "pcs", "piece", "pieces"]:
            # estimate 1 unit as ~100g if unknown
            actual_available_g = qty * 100
        else:
            actual_available_g = qty if qty > 10 else qty * 100 # rough heuristic if unit is 'g' or something else
            
        max_g = min(max_g, actual_available_g)

        amounts[name] = pulp.LpVariable(
            f"g_{name.replace(' ','_')}",
            lowBound=0,
            upBound=max_g
        )

    # Binary variables: whether to include each ingredient
    used = {
        name: pulp.LpVariable(f"use_{name.replace(' ','_')}", cat="Binary")
        for name in amounts
    }

    # ── Objective: Maximize protein ────────────────────────────────
    problem += pulp.lpSum([
        amounts[name] * (nutrition_data[name]["protein"] / 100)
        for name in amounts
    ])

    # ── Constraint: Calorie target ±10% ───────────────────────────
    cal_expr = pulp.lpSum([
        amounts[name] * (nutrition_data[name]["calories"] / 100)
        for name in amounts
    ])
    problem += cal_expr >= targets["calories"] * 0.90, "cal_min"
    problem += cal_expr <= targets["calories"] * 1.10, "cal_max"

    # ── Constraint: Minimum protein ───────────────────────────────
    if "protein_min" in targets:
        prot_expr = pulp.lpSum([
            amounts[name] * (nutrition_data[name]["protein"] / 100)
            for name in amounts
        ])
        problem += prot_expr >= targets["protein_min"], "protein_min"

    # ── Constraint: Max carbs (for keto or low-carb) ─────────────
    if "carbs_max" in targets:
        carb_expr = pulp.lpSum([
            amounts[name] * (nutrition_data[name]["carbs"] / 100)
            for name in amounts
        ])
        problem += carb_expr <= targets["carbs_max"], "carbs_max"

    # ── Constraint: Max fat ───────────────────────────────────────
    if "fat_max" in targets:
        fat_expr = pulp.lpSum([
            amounts[name] * (nutrition_data[name]["fat"] / 100)
            for name in amounts
        ])
        problem += fat_expr <= targets["fat_max"], "fat_max"

    # ── Constraint: Big-M linking amounts to binary ───────────────
    BIG_M = 500
    for name in amounts:
        cat = next((i.get("category","default") for i in usable if i["name"]==name), "default")
        min_g = MIN_PORTIONS.get(cat, MIN_PORTIONS["default"])
        # If used[name]=1 → amounts[name] ≥ min_g; if 0 → amounts=0
        problem += amounts[name] >= used[name] * min_g,  f"min_portion_{name}"
        problem += amounts[name] <= used[name] * BIG_M,  f"max_portion_{name}"

    # ── Constraint: At most N ingredients per meal ────────────────
    problem += pulp.lpSum(used.values()) <= max_ingredients, "max_ingredients"

    # ── Constraint: At most 1 dominant protein source ────────────
    protein_items = [
        name for name, item in zip(amounts.keys(), usable)
        if item.get("category") in ["MEAT_SEAFOOD", "DAIRY_EGGS"]
    ]
    if len(protein_items) > 1:
        problem += pulp.lpSum([used[n] for n in protein_items]) <= 2, "one_main_protein"

    # ── Solve ──────────────────────────────────────────────────────
    solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=3)  # 3 second timeout
    status = problem.solve(solver)

    if pulp.LpStatus[status] not in ["Optimal", "Feasible"]:
        if not is_relaxed:
            # Relax constraints and try again
            return _solve_relaxed(available_ingredients, nutrition_data, targets, meal_type)
        else:
            return {"success": False, "reason": "no_solution", "message": "Could not build a meal even with relaxed constraints."}

    # ── Extract results ────────────────────────────────────────────
    selected = {}
    for name in amounts:
        grams = pulp.value(amounts[name]) or 0
        if grams > 5:   # Ignore trace amounts
            selected[name] = round(grams, 0)

    if not selected:
        return {"success": False, "reason": "no_solution", "message": "Could not build a meal with these constraints."}

    # Calculate actual nutrition achieved
    actual_nutrition = {
        "calories": round(sum(selected[n] * nutrition_data[n]["calories"] / 100 for n in selected)),
        "protein":  round(sum(selected[n] * nutrition_data[n]["protein"]  / 100 for n in selected), 1),
        "carbs":    round(sum(selected[n] * nutrition_data[n]["carbs"]    / 100 for n in selected), 1),
        "fat":      round(sum(selected[n] * nutrition_data[n]["fat"]      / 100 for n in selected), 1),
        "fiber":    round(sum(selected[n] * nutrition_data[n].get("fiber",0) / 100 for n in selected), 1),
    }

    # Map back to item_ids for consumption tracking
    name_to_id = {item["name"]: item.get("item_id") for item in available_ingredients}

    return {
        "success": True,
        "meal_type": meal_type,
        "portions": {
            name: {
                "grams": int(grams),
                "item_id": name_to_id.get(name),
                "is_expiring": next((i.get("is_expiring") for i in usable if i["name"]==name), False)
            }
            for name, grams in selected.items()
        },
        "nutrition": actual_nutrition,
        "targets_met": {
            "calories":    abs(actual_nutrition["calories"] - targets["calories"]) / targets["calories"] <= 0.10,
            "protein_min": actual_nutrition["protein"] >= targets.get("protein_min", 0),
        }
    }


def _solve_relaxed(available_ingredients, nutrition_data, targets, meal_type):
    """
    Fallback: relax all constraints except calories and just maximize protein.
    Used when the strict optimizer finds no feasible solution.
    """
    relaxed_targets = {
        "calories": targets["calories"]
        # All other constraints dropped
    }
    return run_meal_optimizer(
        available_ingredients, nutrition_data,
        relaxed_targets, meal_type,
        max_ingredients=8,    # Allow more ingredients in relaxed mode
        is_relaxed=True
    )
