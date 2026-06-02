"""
Nutrition Lookup Service.

Maps food items to per-100g macronutrient data from the USDA FoodData Central
dataset. Used by the Nutritional Intelligence feature and the Dietary Agent.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger("pantrymind.nutrition")


class NutritionService:
    """Lookup macronutrients per 100g for food items."""

    # Default per-100g values when item not found
    DEFAULT_NUTRITION = {
        "calories_per_100g": 100,
        "protein_g": 5.0,
        "carbs_g": 15.0,
        "fat_g": 3.0,
        "fiber_g": 2.0,
    }

    def __init__(self, kb_path: str | None = None):
        if kb_path is None:
            kb_path = str(Path(__file__).parent.parent / "data" / "nutrition_kb.json")

        try:
            with open(kb_path, "r") as f:
                self.knowledge_base: list[dict] = json.load(f)
            logger.info(f"Loaded nutrition KB with {len(self.knowledge_base)} items.")
        except FileNotFoundError:
            logger.warning(f"Nutrition KB not found at {kb_path}. Using empty KB.")
            self.knowledge_base = []

        # Build lookup dict
        self._lookup: dict[str, dict] = {}
        for entry in self.knowledge_base:
            name = entry.get("item", "").lower().strip()
            if name:
                self._lookup[name] = entry

    def get_nutrition(self, item_name: str) -> dict:
        """
        Look up per-100g nutrition data for an item.
        Returns dict with calories, protein, carbs, fat, fiber.
        """
        item_lower = item_name.lower().strip()

        # Exact match
        if item_lower in self._lookup:
            entry = self._lookup[item_lower]
            return {
                "item": entry.get("item", item_name),
                "calories_per_100g": entry.get("calories_per_100g", 100),
                "protein_g": entry.get("protein_g", 5.0),
                "carbs_g": entry.get("carbs_g", 15.0),
                "fat_g": entry.get("fat_g", 3.0),
                "fiber_g": entry.get("fiber_g", 2.0),
            }

        # Substring match
        for kb_name, entry in self._lookup.items():
            if kb_name in item_lower or item_lower in kb_name:
                return {
                    "item": entry.get("item", item_name),
                    "calories_per_100g": entry.get("calories_per_100g", 100),
                    "protein_g": entry.get("protein_g", 5.0),
                    "carbs_g": entry.get("carbs_g", 15.0),
                    "fat_g": entry.get("fat_g", 3.0),
                    "fiber_g": entry.get("fiber_g", 2.0),
                }

        return {"item": item_name, **self.DEFAULT_NUTRITION}

    def calculate_intake(self, item_name: str, quantity_grams: float) -> dict:
        """
        Calculate actual macronutrient intake for a consumed quantity.

        Args:
            item_name: Name of the food item.
            quantity_grams: Amount consumed in grams.

        Returns:
            {
                "item": "chicken breast",
                "quantity_grams": 200,
                "calories": 330,
                "protein_g": 62.0,
                "carbs_g": 0.0,
                "fat_g": 7.2,
                "fiber_g": 0.0
            }
        """
        nutrition = self.get_nutrition(item_name)
        factor = quantity_grams / 100.0

        return {
            "item": nutrition["item"],
            "quantity_grams": quantity_grams,
            "calories": round(nutrition["calories_per_100g"] * factor, 1),
            "protein_g": round(nutrition["protein_g"] * factor, 1),
            "carbs_g": round(nutrition["carbs_g"] * factor, 1),
            "fat_g": round(nutrition["fat_g"] * factor, 1),
            "fiber_g": round(nutrition["fiber_g"] * factor, 1),
        }

    def check_rda_compliance(self, daily_intake: dict) -> dict:
        """
        Compare daily intake against Recommended Daily Allowances.

        Args:
            daily_intake: {"calories": X, "protein_g": X, "carbs_g": X, ...}

        Returns:
            {
                "calories": {"actual": 1800, "rda": 2000, "status": "deficit", "pct": 90},
                "protein_g": {"actual": 45, "rda": 50, "status": "deficit", "pct": 90},
                ...
            }
        """
        # Standard RDA values (adult, moderate activity)
        rda = {
            "calories": 2000,
            "protein_g": 50,
            "carbs_g": 300,
            "fat_g": 65,
            "fiber_g": 25,
        }

        report = {}
        for nutrient, target in rda.items():
            actual = daily_intake.get(nutrient, 0)
            pct = round((actual / target) * 100, 1) if target > 0 else 0

            if pct >= 90:
                status = "adequate"
            elif pct >= 70:
                status = "low"
            else:
                status = "deficit"

            report[nutrient] = {
                "actual": round(actual, 1),
                "rda": target,
                "status": status,
                "pct": pct,
            }

        return report
