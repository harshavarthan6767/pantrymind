#!/usr/bin/env python3
"""Build carbon_kb.json – food carbon-footprint knowledge base.

Source: Our World in Data – "Environmental Impacts of Food Production"
        https://ourworldindata.org/environmental-impacts-of-food

Primary dataset: Poore & Nemecek (2018), "Reducing food's environmental
impacts through producers and consumers", Science 360(6392), pp. 987-992.
DOI: 10.1126/science.aaq0216

Values represent total supply-chain greenhouse-gas emissions in
kg CO₂-equivalents per kg of product.
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
OUTPUT_FILE = OUTPUT_DIR / "carbon_kb.json"

# ---------------------------------------------------------------------------
# Hardcoded CO₂e values (kg CO₂e per kg of product)
# sourced from Our World in Data / Poore & Nemecek 2018
# ---------------------------------------------------------------------------

CARBON_DATA: list[dict[str, Any]] = [
    # --- Proteins ---
    {"name": "Beef (beef herd)", "category": "meat", "co2e_per_kg": 99.48},
    {"name": "Beef (dairy herd)", "category": "meat", "co2e_per_kg": 33.30},
    {"name": "Lamb & Mutton", "category": "meat", "co2e_per_kg": 39.72},
    {"name": "Pork", "category": "meat", "co2e_per_kg": 12.31},
    {"name": "Chicken", "category": "meat", "co2e_per_kg": 9.87},
    {"name": "Turkey", "category": "meat", "co2e_per_kg": 10.90},
    {"name": "Fish (farmed)", "category": "fish_shellfish", "co2e_per_kg": 13.63},
    {"name": "Fish (wild catch)", "category": "fish_shellfish", "co2e_per_kg": 8.60},
    {"name": "Shrimp (farmed)", "category": "fish_shellfish", "co2e_per_kg": 26.87},
    {"name": "Eggs", "category": "dairy", "co2e_per_kg": 4.67},
    # --- Dairy ---
    {"name": "Milk", "category": "dairy", "co2e_per_kg": 3.15},
    {"name": "Cheese", "category": "dairy", "co2e_per_kg": 23.85},
    {"name": "Yogurt", "category": "dairy", "co2e_per_kg": 3.18},
    {"name": "Butter", "category": "dairy", "co2e_per_kg": 11.92},
    # --- Grains & Staples ---
    {"name": "Rice", "category": "grains_pasta", "co2e_per_kg": 4.45},
    {"name": "Wheat & Rye", "category": "grains_pasta", "co2e_per_kg": 1.57},
    {"name": "Oatmeal", "category": "grains_pasta", "co2e_per_kg": 2.48},
    {"name": "Bread", "category": "baked_goods", "co2e_per_kg": 1.60},
    {"name": "Pasta", "category": "grains_pasta", "co2e_per_kg": 1.80},
    # --- Fruits ---
    {"name": "Apples", "category": "fruits", "co2e_per_kg": 0.43},
    {"name": "Bananas", "category": "fruits", "co2e_per_kg": 0.86},
    {"name": "Berries", "category": "fruits", "co2e_per_kg": 1.53},
    {"name": "Citrus Fruit", "category": "fruits", "co2e_per_kg": 0.39},
    {"name": "Grapes", "category": "fruits", "co2e_per_kg": 1.83},
    {"name": "Tomatoes", "category": "produce", "co2e_per_kg": 2.09},
    # --- Vegetables ---
    {"name": "Potatoes", "category": "produce", "co2e_per_kg": 0.46},
    {"name": "Root Vegetables", "category": "produce", "co2e_per_kg": 0.43},
    {"name": "Onions & Leeks", "category": "produce", "co2e_per_kg": 0.50},
    {"name": "Brassicas (cabbage, broccoli)", "category": "produce", "co2e_per_kg": 0.51},
    {"name": "Leafy Greens", "category": "produce", "co2e_per_kg": 0.52},
    {"name": "Peas", "category": "produce", "co2e_per_kg": 0.98},
    # --- Legumes & Nuts ---
    {"name": "Tofu", "category": "other", "co2e_per_kg": 3.16},
    {"name": "Soymilk", "category": "beverages", "co2e_per_kg": 0.98},
    {"name": "Lentils", "category": "other", "co2e_per_kg": 0.90},
    {"name": "Chickpeas", "category": "other", "co2e_per_kg": 0.83},
    {"name": "Nuts (tree nuts)", "category": "nuts", "co2e_per_kg": 0.43},
    {"name": "Groundnuts (peanuts)", "category": "nuts", "co2e_per_kg": 3.23},
    # --- Oils ---
    {"name": "Olive Oil", "category": "condiments", "co2e_per_kg": 5.42},
    {"name": "Palm Oil", "category": "condiments", "co2e_per_kg": 7.61},
    {"name": "Sunflower Oil", "category": "condiments", "co2e_per_kg": 3.60},
    {"name": "Rapeseed / Canola Oil", "category": "condiments", "co2e_per_kg": 3.73},
    {"name": "Soybean Oil", "category": "condiments", "co2e_per_kg": 6.32},
    # --- Beverages ---
    {"name": "Coffee", "category": "beverages", "co2e_per_kg": 28.53},
    {"name": "Tea", "category": "beverages", "co2e_per_kg": 1.94},
    {"name": "Beer", "category": "beverages", "co2e_per_kg": 1.27},
    {"name": "Wine", "category": "beverages", "co2e_per_kg": 1.79},
    # --- Sweeteners ---
    {"name": "Cane Sugar", "category": "condiments", "co2e_per_kg": 3.20},
    {"name": "Beet Sugar", "category": "condiments", "co2e_per_kg": 1.81},
    {"name": "Dark Chocolate", "category": "snacks", "co2e_per_kg": 46.65},
]


def build() -> Path:
    """Write carbon_kb.json and return its path."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        "_meta": {
            "source": "Our World in Data / Poore & Nemecek (2018)",
            "url": "https://ourworldindata.org/environmental-impacts-of-food",
            "unit": "kg CO₂e per kg of product",
            "description": (
                "Total supply-chain greenhouse-gas emissions for common "
                "food products, expressed in kg CO₂-equivalents per kg."
            ),
            "item_count": len(CARBON_DATA),
        },
        "items": CARBON_DATA,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)

    logger.info("Wrote %d items to %s", len(CARBON_DATA), OUTPUT_FILE)
    return OUTPUT_FILE


if __name__ == "__main__":
    out = build()
    print(f"✅  Output written to {out}")
