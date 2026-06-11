import os
from datetime import datetime, timedelta

async def get_smart_inventory_context(user_id: str = None) -> dict:
    """
    Returns inventory as pre-processed, LLM-optimised context.
    Replaces raw get_inventory() in all agent tool calls.
    """
    from services.db_service import get_db

    db = await get_db()
    effective_user_id = user_id or os.getenv("DEMO_USER_ID", "demo_user_001")
    now = datetime.utcnow()
    expiry_soon_cutoff = now + timedelta(days=3)

    items = await db.inventory.find({
        "user_id": effective_user_id,
        "status": {"$in": ["fresh", "expiring", "Fresh", "Expiring Soon", "Critical"]},
        "quantity": {"$gt": 0}
    }).sort("expiry_date", 1).to_list(200)

    if not items:
        return {
            "status": "empty",
            "summary": "Pantry is empty. No ingredients available.",
            "categories": {},
            "expiring_soon": [],
            "total_items": 0,
            "prompt_context": "Pantry is empty. Suggest the user scans a receipt."
        }

    categories = {}
    expiring = []
    expired = []

    for item in items:
        cat = item.get("category", "OTHER")
        if cat not in categories:
            categories[cat] = []

        quantity = item.get("quantity", 0)
        unit = item.get("unit")
        if not unit or str(unit).lower() == "none":
            unit = "item" if quantity == 1 else "items"

        summary = {
            "id": str(item["_id"]),
            "name": item["name"],
            "quantity": quantity,
            "unit": unit,
        }
        expiry_date = item.get("expiry_date")
        if isinstance(expiry_date, str):
            try:
                expiry_date = datetime.fromisoformat(expiry_date.replace("Z", "+00:00"))
                if expiry_date.tzinfo:
                    expiry_date = expiry_date.replace(tzinfo=None)
            except ValueError:
                expiry_date = None

        if expiry_date:
            days_left = (expiry_date - now).days
            summary["days_until_expiry"] = days_left
            if days_left < 0:
                summary["expired"] = True
                expired.append({**summary, "category": cat})
            elif expiry_date <= expiry_soon_cutoff:
                summary["expiring_soon"] = True
                expiring.append({**summary, "category": cat})

        categories[cat].append(summary)

    lines = []
    if expired:
        lines.append(f"EXPIRED: {', '.join(e['name'] for e in expired[:5])}")
    if expiring:
        lines.append(f"⚠️ EXPIRING SOON: {', '.join(e['name'] for e in expiring[:5])}")
    for cat, cat_items in sorted(categories.items()):
        names = [f"{i['name']} ({i['quantity']}{i['unit']})" for i in cat_items]
        lines.append(f"{cat}: {', '.join(names)}")

    return {
        "status": "ok",
        "total_items": len(items),
        "categories": categories,
        "expired": expired,
        "expiring_soon": expiring,
        "prompt_context": f"Available pantry items ({len(items)} total):\n" + "\n".join(lines)
    }
