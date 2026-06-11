import os
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("pantrymind.expiry_agent")


async def estimate_expiry_with_ai(gemini_client, item_name: str, category: str, is_packed: bool = False) -> dict:
    """
    Use Gemini Flash to estimate realistic shelf life for an item.

    Rules:
    - Fresh items: estimate total shelf life, reduce by typical store hold time (30%)
    - Packed items: estimate manufacturer shelf life, subtract 60 days of store time,
      then apply 75% safety factor
    """
    if not gemini_client:
        return {"remaining_days": None, "confidence": 0, "reasoning": "No AI client available"}

    prompt = f"""You are a food safety expert. Estimate the remaining shelf life for this item
purchased TODAY from a retail store in India.

Item: "{item_name}"
Category: "{category}"
Is Packed/Packaged Product: {is_packed}

Rules:
- For FRESH items (fruits, vegetables, meat, dairy, bakery):
  Estimate the total shelf life in days from harvest/production.
  Assume the retail store held the item for approximately 30% of its total shelf life.
  Return the REMAINING safe days from today's purchase date.
  Example: Apple has 7-day total shelf life, store held it ~2 days → 5 days remaining → apply 50% safety → 2-3 days safe.

- For PACKED/PACKAGED items (canned goods, snacks, beverages, dry goods):
  Estimate the manufacturer's total shelf life in days.
  Assume the store stocked it approximately 60 days after manufacture date.
  Calculate remaining shelf life = total - 60 days.
  Apply a 75% safety factor to the remaining shelf life.
  Example: Biscuit has 365-day shelf life, store had it 60 days → 305 days remaining → 75% = 229 days safe.

Return ONLY this JSON (no markdown):
{{"remaining_days": <integer>, "total_shelf_life_days": <integer>, "confidence": <float 0.0-1.0>, "reasoning": "<brief explanation>", "storage_tip": "<one line storage advice>"}}"""

    try:
        from google.genai import types as genai_types
        from services.llm_client import call_gemini_with_retry
        model_name = os.getenv("GEMINI_MODEL", "gemini-3.1-pro")
        response = await call_gemini_with_retry(lambda: gemini_client.aio.models.generate_content(
            model=model_name,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.15,
            )
        ))
        result = json.loads(response.text)
        return result
    except Exception as e:
        logger.warning(f"Expiry estimation failed for '{item_name}': {e}")
        return {"remaining_days": None, "confidence": 0, "reasoning": f"AI estimation failed: {str(e)}"}
