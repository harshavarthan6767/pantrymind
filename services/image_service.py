"""
PantryMind — Product Image Service
Tier 1: Static dataset match (instant, local)
Tier 2: Vertex AI Imagen 4 generation (for novel products)

Images are stored in: frontend/public/product-images/
"""

import os
import logging
from pathlib import Path

from google.genai import types as genai_types

logger = logging.getLogger("pantrymind.image_service")

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
PRODUCT_IMAGES_DIR = PROJECT_ROOT / "frontend" / "public" / "product-images"
GENERATED_DIR = PRODUCT_IMAGES_DIR / "generated"
DATASET_DIR = PRODUCT_IMAGES_DIR / "dataset"

# Ensure directories exist
PRODUCT_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_DIR.mkdir(parents=True, exist_ok=True)
DATASET_DIR.mkdir(parents=True, exist_ok=True)

# Imagen model — configurable via .env. Using imagen-3.0-fast-generate-001 for faster, more cost-effective generation.
IMAGEN_MODEL = os.getenv("IMAGEN_MODEL", "imagen-3.0-fast-generate-001")

from data.product_images import find_product_image
from services.prompt_agent import generate_image_prompt
from services.product_api_service import search_product_image


def get_product_image_url(item_name: str, item_id: str | None = None) -> str | None:
    """
    Get the URL path for a product image.
    Returns a URL path like /product-images/dataset/chicken.webp or
    /product-images/generated/{item_id}.webp, or None.
    """
    # Tier 1: Check static dataset
    dataset_match = find_product_image(item_name)
    if dataset_match:
        dataset_path = DATASET_DIR / dataset_match
        if dataset_path.exists():
            return f"/product-images/dataset/{dataset_match}"

    # Tier 2: Check if we already generated one for this item
    if item_id:
        generated_path = GENERATED_DIR / f"{item_id}.webp"
        if generated_path.exists():
            return f"/product-images/generated/{item_id}.webp"

    return None


async def generate_product_image_data(gemini_client, item_name: str) -> tuple[bytes, str] | tuple[None, None]:
    """
    Generate a product image using Vertex AI Imagen 4 and return (image_bytes, content_type).
    """
    if not gemini_client:
        logger.warning("No Gemini client available for image generation")
        return None, None

    try:
        prompt = await generate_image_prompt(item_name)
        logger.info(f"Generating image for '{item_name}' with model={IMAGEN_MODEL}")

        response = await gemini_client.aio.models.generate_images(
            model=IMAGEN_MODEL,
            prompt=prompt,
            config=genai_types.GenerateImagesConfig(
                number_of_images=1,
            )
        )

        if response.generated_images and len(response.generated_images) > 0:
            image_data = response.generated_images[0].image.image_bytes
            import base64
            if isinstance(image_data, bytes) and image_data.startswith(b'iVBORw'):
                image_data = base64.b64decode(image_data)
            elif isinstance(image_data, str):
                image_data = base64.b64decode(image_data)

            # Resize and format as webp
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(image_data))
            img = img.resize((512, 512), Image.LANCZOS)
            out_io = io.BytesIO()
            img.save(out_io, "WEBP", quality=85)
            
            return out_io.getvalue(), "image/webp"
        else:
            logger.warning(f"Imagen returned no images for '{item_name}'")
            return None, None
    except Exception as e:
        logger.error(f"Image generation failed for '{item_name}': {type(e).__name__}: {e}")
        return None, None


async def assign_product_image(db_service, gemini_client, item_id: str, item_name: str):
    """
    Background task: assign an image to an inventory item.
    Tries static dataset first, then Cloud DB, OpenFoodFacts, and finally Imagen 4.
    """
    import re
    from bson import ObjectId
    slug = re.sub(r'[^a-z0-9]+', '-', item_name.lower()).strip('-')

    # Tier 0: Check MongoDB cloud cache
    if slug:
        cloud_img = await db_service.find_one("cloud_images", {"slug": slug})
        if cloud_img:
            image_url = f"/api/images/cloud/{slug}"
            await db_service.update_one(
                "inventory",
                {"_id": ObjectId(item_id)},
                {"$set": {"image_url": image_url}}
            )
            logger.info(f"Assigned cloud image for '{item_name}'")
            return

    # Tier 1: Check static dataset
    image_url = get_product_image_url(item_name, item_id)

    # Tier 2: Check OpenFoodFacts
    if not image_url:
        image_url = await search_product_image(item_name)

    # Tier 3: AI Generation (Prompt Manager + Imagen 4)
    if not image_url and gemini_client:
        image_data, content_type = await generate_product_image_data(gemini_client, item_name)
        if image_data:
            import base64
            encoded = base64.b64encode(image_data).decode("utf-8")
            if slug:
                await db_service.insert_one("cloud_images", {
                    "name": item_name,
                    "slug": slug,
                    "image_base64": encoded,
                    "content_type": content_type
                })
                image_url = f"/api/images/cloud/{slug}"

    if image_url:
        await db_service.update_one(
            "inventory",
            {"_id": ObjectId(item_id)},
            {"$set": {"image_url": image_url}}
        )
        logger.info(f"Assigned image for '{item_name}': {image_url}")
