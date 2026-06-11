"""
PantryMind — Medical Condition Research Agent
Uses Gemini to research health conditions and provide dietary guidance.
"""

import os
import json
import logging
from datetime import datetime, timezone
from google.genai import types as genai_types

logger = logging.getLogger("pantrymind.medical_agent")


async def research_condition(gemini_client, condition_name: str) -> dict:
    """
    Uses Gemini to deep-research a medical condition.
    Returns structured data about dietary restrictions, medicines, treatments.
    """
    model = os.getenv("GEMINI_MODEL", "gemini-3.1-pro")

    prompt = f"""You are a medical nutrition research assistant. Research the medical condition: "{condition_name}"

Return a JSON object with EXACTLY this structure (no markdown, no code fences, just raw JSON):
{{
  "condition_name": "{condition_name}",
  "foods_to_avoid": ["list of specific foods/ingredients to avoid"],
  "foods_to_eat": ["list of specific foods/ingredients recommended"],
  "medicines": [
    {{"name": "medicine name", "purpose": "what it does", "dosage": "typical dosage"}}
  ],
  "treatments": ["list of recommended treatments/lifestyle changes"],
  "dietary_notes": "A 2-3 sentence summary of dietary guidelines for this condition",
  "severity_note": "Brief note about consulting a doctor"
}}

Be thorough with the foods lists - include at least 10 items in each. Include common Indian foods where relevant."""

    try:
        response = await gemini_client.aio.models.generate_content(
            model=model,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json",
            )
        )

        text = response.text.strip()
        result = json.loads(text)
        result["researched"] = True
        result["research_source"] = model
        result["researched_at"] = datetime.now(timezone.utc).isoformat()
        return result

    except Exception as e:
        logger.error(f"Medical research failed for '{condition_name}': {e}")
        return {
            "condition_name": condition_name,
            "researched": False,
            "error": str(e),
            "foods_to_avoid": [],
            "foods_to_eat": [],
            "medicines": [],
            "treatments": [],
            "dietary_notes": "Research pending - please consult a healthcare provider.",
        }


async def check_inventory_safety(gemini_client, db_service, user_id: str = "default_user") -> dict:
    """
    2nd line of defence: cross-checks inventory items against medical restrictions.
    Uses Gemini to identify potentially harmful items.
    """
    conditions = await db_service.find("medical_conditions", {"user_id": user_id})
    if not conditions:
        return {"status": "ok", "message": "No medical conditions on file", "flagged_items": []}

    all_avoid = []
    condition_names = []
    for c in conditions:
        all_avoid.extend(c.get("foods_to_avoid", []))
        condition_names.append(c.get("condition_name", "Unknown"))

    if not all_avoid:
        return {"status": "ok", "message": "No dietary restrictions found", "flagged_items": []}

    inventory = await db_service.find("inventory", {}, limit=200)
    if not inventory:
        return {"status": "ok", "message": "Inventory is empty", "flagged_items": []}

    item_names = [item.get("name", "") for item in inventory]

    model = os.getenv("GEMINI_MODEL", "gemini-3.1-pro")
    prompt = f"""You are a dietary safety checker. The user has these medical conditions: {', '.join(condition_names)}.

Foods they should avoid: {json.dumps(all_avoid)}

Here are the items currently in their pantry inventory:
{json.dumps(item_names)}

Identify which inventory items are potentially harmful or should be avoided given their medical conditions.

Return a JSON array where each entry has:
{{
  "item_name": "the inventory item",
  "reason": "why it's flagged",
  "condition": "which medical condition",
  "severity": "high" or "medium" or "low"
}}

Only include items that are genuinely problematic. Return an empty array [] if nothing is flagged.
Return ONLY the JSON array, no markdown."""

    try:
        response = await gemini_client.aio.models.generate_content(
            model=model,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
            )
        )
        flagged = json.loads(response.text.strip())
        return {"status": "ok", "flagged_items": flagged, "total_checked": len(item_names)}
    except Exception as e:
        logger.error(f"Inventory safety check failed: {e}")
        return {"status": "error", "message": str(e), "flagged_items": []}


async def get_dietary_restrictions(db_service, user_id: str = "default_user") -> dict:
    """
    Aggregates all medical conditions into a combined restriction set
    for the kitchen agent to use.
    """
    conditions = await db_service.find("medical_conditions", {"user_id": user_id})

    all_avoid = set()
    all_eat = set()
    all_notes = []
    condition_names = []

    for c in conditions:
        if c.get("researched"):
            all_avoid.update(c.get("foods_to_avoid", []))
            all_eat.update(c.get("foods_to_eat", []))
            all_notes.append(f"{c['condition_name']}: {c.get('dietary_notes', '')}")
            condition_names.append(c["condition_name"])

    return {
        "conditions": condition_names,
        "foods_to_avoid": sorted(list(all_avoid)),
        "foods_to_eat": sorted(list(all_eat)),
        "dietary_notes": all_notes,
    }
