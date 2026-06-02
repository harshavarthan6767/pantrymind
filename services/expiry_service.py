"""
Food Expiry Prediction Service.

Uses the USDA FoodKeeper knowledge base for fresh produce shelf-life
and deterministic date math for packed goods.

Formula:
  - Fresh: predicted_expiry = purchase_date + shelf_life_days (from USDA KB)
  - Packed: suggested_use_by = expiry_date - (expiry_date - mfg_date) * 0.20
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger("pantrymind.expiry")


class ExpiryService:
    """Deterministic food expiry prediction using USDA FoodKeeper data."""

    # Default shelf life (days) when item not found in KB
    DEFAULT_SHELF_LIFE = 7

    def __init__(self, kb_path: str | None = None):
        if kb_path is None:
            kb_path = str(Path(__file__).parent.parent / "data" / "expiry_kb.json")

        try:
            with open(kb_path, "r") as f:
                self.knowledge_base: list[dict] = json.load(f)
            logger.info(f"Loaded expiry KB with {len(self.knowledge_base)} items.")
        except FileNotFoundError:
            logger.warning(f"Expiry KB not found at {kb_path}. Using empty KB.")
            self.knowledge_base = []

        # Build lookup dict for O(1) access
        self._lookup: dict[str, dict] = {}
        for entry in self.knowledge_base:
            name = entry.get("item_name", "").lower().strip()
            if name:
                self._lookup[name] = entry

    def get_shelf_life(self, item_name: str) -> int:
        """
        Look up shelf life in days for an item.
        Uses fuzzy substring matching if exact match fails.

        Returns shelf_life_days (int).
        """
        item_lower = item_name.lower().strip()

        # Exact match
        if item_lower in self._lookup:
            return self._lookup[item_lower].get(
                "shelf_life_days", self.DEFAULT_SHELF_LIFE
            )

        # Substring match (e.g., "green apples" matches "apple")
        for kb_name, entry in self._lookup.items():
            if kb_name in item_lower or item_lower in kb_name:
                return entry.get("shelf_life_days", self.DEFAULT_SHELF_LIFE)

        logger.debug(f"No KB match for '{item_name}', using default {self.DEFAULT_SHELF_LIFE} days.")
        return self.DEFAULT_SHELF_LIFE

    def predict_expiry_fresh(
        self, item_name: str, purchase_date: str | datetime
    ) -> dict:
        """
        Predict expiry for fresh produce.

        Formula: predicted_expiry = purchase_date + shelf_life_days

        Args:
            item_name: Name of the food item.
            purchase_date: ISO date string or datetime.

        Returns:
            {
                "item_name": "apples",
                "purchase_date": "2026-06-01",
                "shelf_life_days": 28,
                "predicted_expiry": "2026-06-29",
                "storage_method": "Refrigerated",
                "source": "USDA FoodKeeper"
            }
        """
        if isinstance(purchase_date, str):
            purchase_dt = datetime.fromisoformat(
                purchase_date.replace("Z", "+00:00")
            )
        else:
            purchase_dt = purchase_date

        shelf_life = self.get_shelf_life(item_name)
        expiry_dt = purchase_dt + timedelta(days=shelf_life)

        # Get storage method from KB if available
        item_lower = item_name.lower().strip()
        storage = "Refrigerated"
        for kb_name, entry in self._lookup.items():
            if kb_name in item_lower or item_lower in kb_name:
                storage = entry.get("storage_method", "Refrigerated")
                break

        return {
            "item_name": item_name,
            "purchase_date": purchase_dt.strftime("%Y-%m-%d"),
            "shelf_life_days": shelf_life,
            "predicted_expiry": expiry_dt.strftime("%Y-%m-%d"),
            "storage_method": storage,
            "source": "USDA FoodKeeper",
        }

    def calculate_suggested_usage_packed(
        self,
        item_name: str,
        manufacture_date: str | datetime,
        expiry_date: str | datetime,
    ) -> dict:
        """
        Calculate suggested usage date for packed goods.

        Formula: suggested_use_by = expiry - (expiry - mfg) * 0.20
        This ensures consumption at 80% of total shelf life for peak freshness.

        Args:
            item_name: Name of the product.
            manufacture_date: Manufacturing/packing date.
            expiry_date: Printed expiry date on package.

        Returns:
            {
                "item_name": "Dairy Milk Chocolate",
                "manufacture_date": "2026-04-01",
                "expiry_date": "2027-03-01",
                "total_shelf_days": 334,
                "suggested_use_by": "2026-12-14",
                "days_until_suggested": 196,
                "recommendation": "Use before 2026-12-14 for peak freshness."
            }
        """
        if isinstance(manufacture_date, str):
            mfg_dt = datetime.fromisoformat(manufacture_date.replace("Z", "+00:00"))
        else:
            mfg_dt = manufacture_date

        if isinstance(expiry_date, str):
            exp_dt = datetime.fromisoformat(expiry_date.replace("Z", "+00:00"))
        else:
            exp_dt = expiry_date

        total_shelf = (exp_dt - mfg_dt).days
        buffer_days = int(total_shelf * 0.20)
        suggested_dt = exp_dt - timedelta(days=buffer_days)

        days_until = (suggested_dt - datetime.now()).days

        return {
            "item_name": item_name,
            "manufacture_date": mfg_dt.strftime("%Y-%m-%d"),
            "expiry_date": exp_dt.strftime("%Y-%m-%d"),
            "total_shelf_days": total_shelf,
            "suggested_use_by": suggested_dt.strftime("%Y-%m-%d"),
            "days_until_suggested": max(0, days_until),
            "recommendation": (
                f"Use before {suggested_dt.strftime('%Y-%m-%d')} for peak freshness."
            ),
        }
