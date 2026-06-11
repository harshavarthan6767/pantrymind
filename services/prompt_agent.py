import logging
import os
from google.genai import Client

logger = logging.getLogger("pantrymind.prompt_agent")

async def generate_image_prompt(item_name: str, category: str = "Groceries") -> str:
    """
    Generates a highly specific, dimensionally constrained prompt for Imagen 4.
    """
    try:
        client = Client(
            vertexai=True,
            project=os.getenv("GCP_PROJECT"),
            location=os.getenv("GCP_LOCATION", "us-central1")
        )
        
        system_instruction = (
            "You are an expert product photography director. Your job is to take a grocery item "
            "and output a single, highly detailed prompt for an image generation model.\n"
            "CRITICAL CONSTRAINTS FOR THE UI:\n"
            "1. The item must be perfectly centered.\n"
            "2. The item should fill roughly 80% of the frame (slight padding so it isn't cropped but not zoomed out too far).\n"
            "3. The background MUST be absolute pure #FFFFFF white. Completely isolated on white. No environmental backgrounds, no surfaces, no dark corners.\n"
            "4. The style should be appetizing, photorealistic studio photography, brightly lit. DO NOT add heavy drop shadows or dark dramatic lighting.\n"
            "5. NO text, NO labels, NO packaging unless it's a branded liquid.\n"
            "Output ONLY the prompt, nothing else."
        )

        response = await client.aio.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-3.1-pro"),
            contents=f"Item: {item_name}\nCategory: {category}",
            config={
                "system_instruction": system_instruction,
                "temperature": 0.3,
            }
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Failed to generate prompt for {item_name}: {e}")
        # Fallback to a standard prompt with padding instructions
        return (
            f"A professional photorealistic studio photograph of {item_name}, "
            "filling 80% of the frame, perfectly centered. Absolute pure #FFFFFF white background, "
            "completely isolated on white. Brightly lit, highly detailed, appetizing. "
            "No environmental backgrounds, no surfaces, no dark shadows."
        )
