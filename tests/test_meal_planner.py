"""Pytest tests for PuLP meal planning solver."""

import pytest
from pulp import LpMaximize, LpProblem, LpStatus, LpVariable, value


def solve_meal_plan(inventory, calorie_target=2000, protein_min=50):
    """Simple meal planning LP solver.

    inventory: list of dicts with keys: item, quantity_g, cal_per_g, protein_per_g
    Returns: dict with status, selected items, total_calories, total_protein
    """
    prob = LpProblem("MealPlan", LpMaximize)

    # Decision variables: how many grams of each item to use
    vars = {}
    for item in inventory:
        vars[item["item"]] = LpVariable(
            item["item"], lowBound=0, upBound=item["quantity_g"]
        )

    # Objective: maximize protein
    prob += sum(vars[i["item"]] * i["protein_per_g"] for i in inventory)

    # Constraint: meet calorie target (within 10%)
    total_cal = sum(vars[i["item"]] * i["cal_per_g"] for i in inventory)
    prob += total_cal >= calorie_target * 0.9
    prob += total_cal <= calorie_target * 1.1

    # Constraint: minimum protein
    total_protein = sum(vars[i["item"]] * i["protein_per_g"] for i in inventory)
    prob += total_protein >= protein_min

    prob.solve()

    status = LpStatus[prob.status]
    selected = {k: value(v) for k, v in vars.items() if value(v) and value(v) > 0}

    actual_cal = sum(
        selected.get(i["item"], 0) * i["cal_per_g"] for i in inventory
    )
    actual_protein = sum(
        selected.get(i["item"], 0) * i["protein_per_g"] for i in inventory
    )

    return {
        "status": status,
        "selected": selected,
        "total_calories": round(actual_cal, 1),
        "total_protein": round(actual_protein, 1),
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

AMPLE_INVENTORY = [
    {"item": "chicken", "quantity_g": 500, "cal_per_g": 2.39, "protein_per_g": 0.27},
    {"item": "rice", "quantity_g": 800, "cal_per_g": 1.30, "protein_per_g": 0.027},
    {"item": "eggs", "quantity_g": 300, "cal_per_g": 1.55, "protein_per_g": 0.13},
    {"item": "dal", "quantity_g": 400, "cal_per_g": 1.16, "protein_per_g": 0.09},
    {"item": "paneer", "quantity_g": 250, "cal_per_g": 2.65, "protein_per_g": 0.18},
]

TINY_INVENTORY = [
    {"item": "chicken", "quantity_g": 10, "cal_per_g": 2.39, "protein_per_g": 0.27},
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMealPlanner:
    """Tests for the PuLP-based meal planning solver."""

    def test_feasible_solution(self):
        """With ample inventory the solver should find an Optimal solution."""
        result = solve_meal_plan(AMPLE_INVENTORY)
        assert result["status"] == "Optimal"

    def test_infeasible_small_inventory(self):
        """With tiny inventory the solver cannot meet calorie constraints."""
        result = solve_meal_plan(TINY_INVENTORY)
        assert result["status"] == "Infeasible"

    def test_calorie_constraint_met(self):
        """Total calories should be within ±10% of the 2000 kcal target."""
        result = solve_meal_plan(AMPLE_INVENTORY, calorie_target=2000)
        if result["status"] == "Optimal":
            assert 1800 <= result["total_calories"] <= 2200

    def test_protein_minimum_met(self):
        """Total protein should be at least the minimum (50 g)."""
        result = solve_meal_plan(AMPLE_INVENTORY, protein_min=50)
        if result["status"] == "Optimal":
            assert result["total_protein"] >= 50
