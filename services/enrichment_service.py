import httpx
import asyncio
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

logger = logging.getLogger("pantrymind.enrichment")

OPEN_FOOD_FACTS_BASE = "https://world.openfoodfacts.org"


async def enrich_packed_items_background(
    db: AsyncIOMotorDatabase,
    item_ids: list,
    normalized_names: list
):
    """
    Called via FastAPI BackgroundTasks — runs after response is returned.
    Only runs for PACKED products (PANTRY_DRY, SNACKS, CONDIMENTS, BEVERAGES).
    """
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        tasks = [
            _fetch_and_update_item(client, db, item_id, name)
            for item_id, name in zip(item_ids, normalized_names)
        ]
        # Run all enrichment calls concurrently
        await asyncio.gather(*tasks, return_exceptions=True)


async def _fetch_and_update_item(client, db, item_id, normalized_name):
    try:
        # Search Open Food Facts by product name
        response = await client.get(
            f"{OPEN_FOOD_FACTS_BASE}/cgi/search.pl",
            params={
                "search_terms": normalized_name,
                "search_simple": 1,
                "action": "process",
                "json": 1,
                "page_size": 1,
                "fields": "product_name,nutriments,categories,quantity"
            }
        )
        
        data = response.json()
        products = data.get("products", [])
        
        if not products:
            await db["inventory"].update_one(
                {"_id": item_id},
                {"$set": {"enrichment_status": "not_found"}}
            )
            return
        
        product = products[0]
        nutriments = product.get("nutriments", {})
        
        update_data = {
            "enrichment_status": "enriched",
            "nutritional_per_100g": {
                "calories": nutriments.get("energy-kcal_100g"),
                "protein": nutriments.get("proteins_100g"),
                "fat": nutriments.get("fat_100g"),
                "carbs": nutriments.get("carbohydrates_100g"),
                "fiber": nutriments.get("fiber_100g")
            }
        }
        
        await db["inventory"].update_one(
            {"_id": item_id},
            {"$set": update_data}
        )
        
    except Exception as e:
        logger.warning(f"Enrichment failed for {normalized_name}: {e}")
        pass
