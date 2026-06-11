import os
import httpx
import asyncio
from functools import lru_cache
from data.nutrition_db import NUTRITION_DB

USDA_BASE = "https://api.nal.usda.gov/fdc/v1"

@lru_cache(maxsize=512)
async def lookup_nutrition_usda(ingredient_name: str) -> dict:
    """
    Queries USDA FoodData Central for macro data.
    Returns per-100g values. Falls back to estimated averages if not found.
    """
    api_key = os.getenv("USDA_API_KEY")
    if not api_key:
        return _get_category_average_nutrition(ingredient_name)

    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            response = await client.get(
                f"{USDA_BASE}/foods/search",
                params={
                    "query": ingredient_name,
                    "dataType": "Foundation,SR Legacy",
                    "pageSize": 1,
                    "api_key": api_key
                }
            )
            response.raise_for_status()
            data = response.json()
            foods = data.get("foods", [])

            if not foods:
                return _get_category_average_nutrition(ingredient_name)

            food = foods[0]
            nutrients = {n["nutrientName"]: n["value"] for n in food.get("foodNutrients", [])}

            return {
                "calories": round(nutrients.get("Energy", 0)),
                "protein":  round(nutrients.get("Protein", 0), 1),
                "carbs":    round(nutrients.get("Carbohydrate, by difference", 0), 1),
                "fat":      round(nutrients.get("Total lipid (fat)", 0), 1),
                "fiber":    round(nutrients.get("Fiber, total dietary", 0), 1),
                "source":   "usda"
            }
        except Exception:
            return _get_category_average_nutrition(ingredient_name)


def _get_category_average_nutrition(name: str) -> dict:
    """
    Last-resort fallback when USDA doesn't have the item.
    Returns reasonable category averages based on keyword detection.
    """
    name_lower = name.lower()
    if any(w in name_lower for w in ["chicken", "mutton", "fish", "pork", "beef", "meat"]):
        return {"calories": 180, "protein": 25.0, "carbs": 0.0, "fat": 8.0, "fiber": 0.0, "source": "estimated_meat"}
    if any(w in name_lower for w in ["dal", "lentil", "bean", "chana", "rajma"]):
        return {"calories": 360, "protein": 22.0, "carbs": 60.0, "fat": 2.0, "fiber": 12.0, "source": "estimated_legume"}
    if any(w in name_lower for w in ["vegetable", "sabzi", "greens"]):
        return {"calories": 35, "protein": 2.0, "carbs": 7.0, "fat": 0.3, "fiber": 2.5, "source": "estimated_veg"}
    return {"calories": 200, "protein": 8.0, "carbs": 30.0, "fat": 5.0, "fiber": 2.0, "source": "estimated_generic"}


async def get_nutrition_for_items(item_names: list) -> dict:
    """
    Batch nutrition lookup. Checks local DB first, then USDA for misses.
    Used by the LP optimizer before running.
    """
    result = {}
    usda_lookups = []

    for name in item_names:
        if name in NUTRITION_DB:
            result[name] = NUTRITION_DB[name]
        else:
            usda_lookups.append(name)

    if usda_lookups:
        usda_results = await asyncio.gather(*[
            lookup_nutrition_usda(name) for name in usda_lookups
        ])
        for name, nutrition in zip(usda_lookups, usda_results):
            result[name] = nutrition

    return result
