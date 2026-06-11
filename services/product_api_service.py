import logging
import httpx

logger = logging.getLogger("pantrymind.product_api")

async def search_product_image(item_name: str) -> str | None:
    """
    Search OpenFoodFacts for the item_name and return an image URL if found.
    Returns None if not found or on error.
    """
    try:
        url = "https://world.openfoodfacts.org/cgi/search.pl"
        params = {
            "search_terms": item_name,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 1
        }
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("products") and len(data["products"]) > 0:
                product = data["products"][0]
                # Try to get the front image, or selected image, or image_url
                img_url = product.get("image_front_url") or product.get("image_url")
                if img_url:
                    logger.info(f"Found real product image for '{item_name}' via OpenFoodFacts")
                    return img_url
                    
        return None
    except Exception as e:
        logger.warning(f"Failed to search OpenFoodFacts for '{item_name}': {e}")
        return None
