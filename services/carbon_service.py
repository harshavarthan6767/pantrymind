"""
Carbon Footprint Service.

Maps food purchases to CO₂ equivalent emissions using the Our World in Data
dataset (global averages per kg of food production).

Source: https://ourworldindata.org/food-choice-vs-eating-local
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger("pantrymind.carbon")


class CarbonService:
    """Lookup CO₂e per kg for food items."""

    # Fallback CO₂e per kg when item not in KB
    DEFAULT_CO2_PER_KG = 2.0

    def __init__(self, kb_path: str | None = None):
        if kb_path is None:
            kb_path = str(Path(__file__).parent.parent / "data" / "carbon_kb.json")

        try:
            with open(kb_path, "r") as f:
                self.knowledge_base: list[dict] = json.load(f)
            logger.info(f"Loaded carbon KB with {len(self.knowledge_base)} items.")
        except FileNotFoundError:
            logger.warning(f"Carbon KB not found at {kb_path}. Using empty KB.")
            self.knowledge_base = []

        # Build lookup dict
        self._lookup: dict[str, dict] = {}
        for entry in self.knowledge_base:
            name = entry.get("item", "").lower().strip()
            if name:
                self._lookup[name] = entry

    def get_co2_per_kg(self, item_name: str) -> float:
        """
        Look up CO₂e per kg for an item.
        Uses fuzzy substring matching if exact match fails.
        """
        item_lower = item_name.lower().strip()

        # Exact match
        if item_lower in self._lookup:
            return self._lookup[item_lower].get("co2_per_kg", self.DEFAULT_CO2_PER_KG)

        # Substring match
        for kb_name, entry in self._lookup.items():
            if kb_name in item_lower or item_lower in kb_name:
                return entry.get("co2_per_kg", self.DEFAULT_CO2_PER_KG)

        return self.DEFAULT_CO2_PER_KG

    def calculate_impact(self, item_name: str, quantity_kg: float) -> dict:
        """
        Calculate CO₂ impact for a specific purchase.

        Returns:
            {
                "item_name": "beef",
                "quantity_kg": 0.5,
                "co2_per_kg": 60.0,
                "total_co2_kg": 30.0,
                "category": "meat",
                "impact_level": "very_high"
            }
        """
        co2_per_kg = self.get_co2_per_kg(item_name)
        total_co2 = co2_per_kg * quantity_kg

        # Classify impact level
        if co2_per_kg >= 20:
            level = "very_high"
        elif co2_per_kg >= 10:
            level = "high"
        elif co2_per_kg >= 5:
            level = "moderate"
        elif co2_per_kg >= 2:
            level = "low"
        else:
            level = "very_low"

        # Get category from KB
        item_lower = item_name.lower().strip()
        category = "unknown"
        for kb_name, entry in self._lookup.items():
            if kb_name in item_lower or item_lower in kb_name:
                category = entry.get("category", "unknown")
                break

        return {
            "item_name": item_name,
            "quantity_kg": quantity_kg,
            "co2_per_kg": co2_per_kg,
            "total_co2_kg": round(total_co2, 2),
            "category": category,
            "impact_level": level,
        }

    def suggest_green_swap(self, item_name: str) -> dict | None:
        """
        Suggest a lower-CO₂ alternative for a high-impact item.
        Returns None if the item is already low-impact.
        """
        co2 = self.get_co2_per_kg(item_name)
        if co2 < 5:
            return None  # Already low impact

        # Find items in same category with lower CO₂
        item_lower = item_name.lower().strip()
        current_category = "unknown"
        for kb_name, entry in self._lookup.items():
            if kb_name in item_lower or item_lower in kb_name:
                current_category = entry.get("category", "unknown")
                break

        # Find best alternative in same category
        alternatives = [
            entry
            for entry in self.knowledge_base
            if entry.get("category") == current_category
            and entry.get("co2_per_kg", 999) < co2
        ]

        if not alternatives:
            # Cross-category: find any protein alternative
            alternatives = [
                entry
                for entry in self.knowledge_base
                if entry.get("co2_per_kg", 999) < co2 * 0.5
            ]

        if alternatives:
            best = min(alternatives, key=lambda x: x.get("co2_per_kg", 999))
            savings = co2 - best["co2_per_kg"]
            return {
                "current_item": item_name,
                "current_co2": co2,
                "suggested_item": best["item"],
                "suggested_co2": best["co2_per_kg"],
                "savings_per_kg": round(savings, 2),
                "reduction_pct": round((savings / co2) * 100, 1),
            }

        return None
