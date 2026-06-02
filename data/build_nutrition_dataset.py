#!/usr/bin/env python3
"""Build nutrition_kb.json – food nutrition knowledge base.

Source: USDA FoodData Central (fdc.nal.usda.gov)
        https://fdc.nal.usda.gov/

Values are per 100 g of edible portion (Survey / SR Legacy reference).
Nutrient data from USDA National Nutrient Database for Standard Reference.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = OUTPUT_DIR / "nutrition_kb.json"

# ---------------------------------------------------------------------------
# Hardcoded nutrition data – per 100 g of edible portion
# Key nutrients: calories (kcal), protein (g), fat (g), carbs (g), fiber (g)
# ---------------------------------------------------------------------------

NUTRITION_DATA: list[dict[str, Any]] = [
    # --- Fruits ---
    {"name": "Apple, raw", "category": "fruits",
     "per_100g": {"calories": 52, "protein": 0.3, "fat": 0.2, "carbs": 13.8, "fiber": 2.4}},
    {"name": "Banana, raw", "category": "fruits",
     "per_100g": {"calories": 89, "protein": 1.1, "fat": 0.3, "carbs": 22.8, "fiber": 2.6}},
    {"name": "Strawberry, raw", "category": "fruits",
     "per_100g": {"calories": 32, "protein": 0.7, "fat": 0.3, "carbs": 7.7, "fiber": 2.0}},
    {"name": "Blueberry, raw", "category": "fruits",
     "per_100g": {"calories": 57, "protein": 0.7, "fat": 0.3, "carbs": 14.5, "fiber": 2.4}},
    {"name": "Orange, raw", "category": "fruits",
     "per_100g": {"calories": 47, "protein": 0.9, "fat": 0.1, "carbs": 11.8, "fiber": 2.4}},
    {"name": "Grapes, raw", "category": "fruits",
     "per_100g": {"calories": 69, "protein": 0.7, "fat": 0.2, "carbs": 18.1, "fiber": 0.9}},
    {"name": "Avocado, raw", "category": "fruits",
     "per_100g": {"calories": 160, "protein": 2.0, "fat": 14.7, "carbs": 8.5, "fiber": 6.7}},
    {"name": "Mango, raw", "category": "fruits",
     "per_100g": {"calories": 60, "protein": 0.8, "fat": 0.4, "carbs": 15.0, "fiber": 1.6}},
    # --- Vegetables ---
    {"name": "Broccoli, raw", "category": "produce",
     "per_100g": {"calories": 34, "protein": 2.8, "fat": 0.4, "carbs": 6.6, "fiber": 2.6}},
    {"name": "Spinach, raw", "category": "produce",
     "per_100g": {"calories": 23, "protein": 2.9, "fat": 0.4, "carbs": 3.6, "fiber": 2.2}},
    {"name": "Carrot, raw", "category": "produce",
     "per_100g": {"calories": 41, "protein": 0.9, "fat": 0.2, "carbs": 9.6, "fiber": 2.8}},
    {"name": "Potato, raw", "category": "produce",
     "per_100g": {"calories": 77, "protein": 2.0, "fat": 0.1, "carbs": 17.5, "fiber": 2.2}},
    {"name": "Sweet Potato, raw", "category": "produce",
     "per_100g": {"calories": 86, "protein": 1.6, "fat": 0.1, "carbs": 20.1, "fiber": 3.0}},
    {"name": "Tomato, raw", "category": "produce",
     "per_100g": {"calories": 18, "protein": 0.9, "fat": 0.2, "carbs": 3.9, "fiber": 1.2}},
    {"name": "Bell Pepper, raw", "category": "produce",
     "per_100g": {"calories": 26, "protein": 1.0, "fat": 0.3, "carbs": 6.0, "fiber": 2.1}},
    {"name": "Onion, raw", "category": "produce",
     "per_100g": {"calories": 40, "protein": 1.1, "fat": 0.1, "carbs": 9.3, "fiber": 1.7}},
    {"name": "Garlic, raw", "category": "produce",
     "per_100g": {"calories": 149, "protein": 6.4, "fat": 0.5, "carbs": 33.1, "fiber": 2.1}},
    {"name": "Lettuce, iceberg", "category": "produce",
     "per_100g": {"calories": 14, "protein": 0.9, "fat": 0.1, "carbs": 3.0, "fiber": 1.2}},
    # --- Meat ---
    {"name": "Chicken breast, raw", "category": "meat",
     "per_100g": {"calories": 120, "protein": 22.5, "fat": 2.6, "carbs": 0.0, "fiber": 0.0}},
    {"name": "Beef, ground (85% lean)", "category": "meat",
     "per_100g": {"calories": 215, "protein": 18.6, "fat": 15.0, "carbs": 0.0, "fiber": 0.0}},
    {"name": "Pork chop, raw", "category": "meat",
     "per_100g": {"calories": 154, "protein": 21.0, "fat": 7.1, "carbs": 0.0, "fiber": 0.0}},
    {"name": "Turkey breast, raw", "category": "meat",
     "per_100g": {"calories": 104, "protein": 23.7, "fat": 0.7, "carbs": 0.0, "fiber": 0.0}},
    {"name": "Lamb, leg, raw", "category": "meat",
     "per_100g": {"calories": 162, "protein": 20.3, "fat": 8.8, "carbs": 0.0, "fiber": 0.0}},
    {"name": "Bacon, raw", "category": "meat",
     "per_100g": {"calories": 417, "protein": 12.6, "fat": 40.3, "carbs": 1.4, "fiber": 0.0}},
    # --- Fish & Shellfish ---
    {"name": "Salmon, Atlantic, raw", "category": "fish_shellfish",
     "per_100g": {"calories": 208, "protein": 20.4, "fat": 13.4, "carbs": 0.0, "fiber": 0.0}},
    {"name": "Tuna, raw", "category": "fish_shellfish",
     "per_100g": {"calories": 130, "protein": 28.2, "fat": 1.3, "carbs": 0.0, "fiber": 0.0}},
    {"name": "Shrimp, raw", "category": "fish_shellfish",
     "per_100g": {"calories": 85, "protein": 20.1, "fat": 0.5, "carbs": 0.9, "fiber": 0.0}},
    {"name": "Cod, raw", "category": "fish_shellfish",
     "per_100g": {"calories": 82, "protein": 17.8, "fat": 0.7, "carbs": 0.0, "fiber": 0.0}},
    # --- Dairy ---
    {"name": "Milk, whole (3.25%)", "category": "dairy",
     "per_100g": {"calories": 61, "protein": 3.2, "fat": 3.3, "carbs": 4.8, "fiber": 0.0}},
    {"name": "Cheddar cheese", "category": "dairy",
     "per_100g": {"calories": 403, "protein": 24.9, "fat": 33.1, "carbs": 1.3, "fiber": 0.0}},
    {"name": "Yogurt, plain, whole milk", "category": "dairy",
     "per_100g": {"calories": 61, "protein": 3.5, "fat": 3.3, "carbs": 4.7, "fiber": 0.0}},
    {"name": "Butter, salted", "category": "dairy",
     "per_100g": {"calories": 717, "protein": 0.9, "fat": 81.1, "carbs": 0.1, "fiber": 0.0}},
    {"name": "Egg, whole, raw", "category": "dairy",
     "per_100g": {"calories": 143, "protein": 12.6, "fat": 9.5, "carbs": 0.7, "fiber": 0.0}},
    {"name": "Cream cheese", "category": "dairy",
     "per_100g": {"calories": 342, "protein": 5.9, "fat": 34.2, "carbs": 4.1, "fiber": 0.0}},
    # --- Grains & Pasta ---
    {"name": "Rice, white, long-grain, raw", "category": "grains_pasta",
     "per_100g": {"calories": 365, "protein": 7.1, "fat": 0.7, "carbs": 80.0, "fiber": 1.3}},
    {"name": "Rice, brown, raw", "category": "grains_pasta",
     "per_100g": {"calories": 370, "protein": 7.9, "fat": 2.9, "carbs": 77.2, "fiber": 3.5}},
    {"name": "Pasta, dry", "category": "grains_pasta",
     "per_100g": {"calories": 371, "protein": 13.0, "fat": 1.5, "carbs": 74.7, "fiber": 3.2}},
    {"name": "Oats, rolled, dry", "category": "grains_pasta",
     "per_100g": {"calories": 389, "protein": 16.9, "fat": 6.9, "carbs": 66.3, "fiber": 10.6}},
    {"name": "Bread, white", "category": "baked_goods",
     "per_100g": {"calories": 265, "protein": 9.4, "fat": 3.3, "carbs": 49.2, "fiber": 2.7}},
    {"name": "Bread, whole wheat", "category": "baked_goods",
     "per_100g": {"calories": 247, "protein": 12.9, "fat": 3.4, "carbs": 41.3, "fiber": 6.8}},
    # --- Legumes ---
    {"name": "Lentils, raw", "category": "other",
     "per_100g": {"calories": 352, "protein": 24.6, "fat": 1.1, "carbs": 63.4, "fiber": 10.7}},
    {"name": "Chickpeas, raw", "category": "other",
     "per_100g": {"calories": 364, "protein": 19.3, "fat": 6.0, "carbs": 60.7, "fiber": 17.4}},
    {"name": "Black beans, raw", "category": "other",
     "per_100g": {"calories": 341, "protein": 21.6, "fat": 1.4, "carbs": 62.4, "fiber": 15.5}},
    {"name": "Tofu, firm", "category": "other",
     "per_100g": {"calories": 144, "protein": 15.6, "fat": 8.7, "carbs": 2.8, "fiber": 1.2}},
    # --- Nuts & Seeds ---
    {"name": "Almonds", "category": "nuts",
     "per_100g": {"calories": 579, "protein": 21.2, "fat": 49.9, "carbs": 21.6, "fiber": 12.5}},
    {"name": "Walnuts", "category": "nuts",
     "per_100g": {"calories": 654, "protein": 15.2, "fat": 65.2, "carbs": 13.7, "fiber": 6.7}},
    {"name": "Peanuts", "category": "nuts",
     "per_100g": {"calories": 567, "protein": 25.8, "fat": 49.2, "carbs": 16.1, "fiber": 8.5}},
    {"name": "Chia seeds", "category": "nuts",
     "per_100g": {"calories": 486, "protein": 16.5, "fat": 30.7, "carbs": 42.1, "fiber": 34.4}},
    {"name": "Sunflower seeds", "category": "nuts",
     "per_100g": {"calories": 584, "protein": 20.8, "fat": 51.5, "carbs": 20.0, "fiber": 8.6}},
    # --- Condiments & Oils ---
    {"name": "Olive oil", "category": "condiments",
     "per_100g": {"calories": 884, "protein": 0.0, "fat": 100.0, "carbs": 0.0, "fiber": 0.0}},
    {"name": "Honey", "category": "condiments",
     "per_100g": {"calories": 304, "protein": 0.3, "fat": 0.0, "carbs": 82.4, "fiber": 0.2}},
    {"name": "Soy sauce", "category": "condiments",
     "per_100g": {"calories": 53, "protein": 8.1, "fat": 0.0, "carbs": 4.9, "fiber": 0.8}},
    # --- Beverages ---
    {"name": "Orange juice", "category": "beverages",
     "per_100g": {"calories": 45, "protein": 0.7, "fat": 0.2, "carbs": 10.4, "fiber": 0.2}},
    {"name": "Coffee, brewed", "category": "beverages",
     "per_100g": {"calories": 1, "protein": 0.1, "fat": 0.0, "carbs": 0.0, "fiber": 0.0}},
]


def build() -> Path:
    """Write nutrition_kb.json and return its path."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        "_meta": {
            "source": "USDA FoodData Central",
            "url": "https://fdc.nal.usda.gov/",
            "unit": "per 100 g edible portion",
            "nutrients": {
                "calories": "kcal",
                "protein": "g",
                "fat": "g",
                "carbs": "g",
                "fiber": "g",
            },
            "description": (
                "Macronutrient profiles for common food items, "
                "derived from the USDA National Nutrient Database "
                "for Standard Reference (SR Legacy)."
            ),
            "item_count": len(NUTRITION_DATA),
        },
        "items": NUTRITION_DATA,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)

    logger.info("Wrote %d items to %s", len(NUTRITION_DATA), OUTPUT_FILE)
    return OUTPUT_FILE


if __name__ == "__main__":
    out = build()
    print(f"✅  Output written to {out}")
