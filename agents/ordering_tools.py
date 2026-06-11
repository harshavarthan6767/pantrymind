import json
import random
import logging
from datetime import datetime, timezone
from bson import ObjectId

logger = logging.getLogger("pantrymind.ordering")

import asyncio
from datetime import datetime, timedelta
from bson import ObjectId

PRICE_DB = {
    "rice": 45,
    "dal": 120,
    "wheat flour": 45,
    "atta": 45,
    "oil": 150,
    "onion": 30,
    "tomato": 40,
    "potato": 25,
    "garlic": 80,
    "ginger": 120,
    "milk": 60,
    "curd": 50,
    "eggs": 8,
    "egg": 8,
    "chicken": 300,
    "paneer": 350,
    "bread": 40,
    "salt": 20,
    "sugar": 45,
    "default": 80,
}

def _clamp_price(price: float, unit: str) -> float:
    """Prevent astronomical mock prices for weight-based units."""
    if unit in ("kg", "g"):   return min(price, 500.0)
    if unit in ("ml", "l"):   return min(price, 300.0)
    return min(price, 1000.0)

def _quantity_number(value, default: float = 1.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        import re
        match = re.search(r"\d+(?:\.\d+)?", value)
        if match:
            return float(match.group(0))
    return default

def _unit_for(item: dict) -> str:
    unit = str(item.get("unit") or "").strip().lower()
    quantity = str(item.get("quantity") or "").strip().lower()
    if unit:
        return unit
    for candidate in ("kg", "g", "ml", "l", "litre", "liter", "pcs", "piece", "unit"):
        if candidate in quantity:
            return candidate
    return "unit"

def _base_price_for(item: dict) -> float:
    name = str(item.get("name") or item.get("item") or "").lower()
    for key, price in PRICE_DB.items():
        if key != "default" and (key in name or name in key):
            return float(price)
    return float(PRICE_DB["default"])

def _item_total(item: dict) -> float:
    """Return the estimated total cost for one requested order line."""
    explicit_total = item.get("estimated_cost") or item.get("total_cost") or item.get("total")
    if explicit_total is not None:
        return round(float(explicit_total), 2)

    unit = _unit_for(item)
    qty = _quantity_number(item.get("quantity") or item.get("suggested_qty"), 1)
    unit_price = _clamp_price(float(item.get("estimated_price") or _base_price_for(item)), unit)

    if unit == "g":
        cost = unit_price * (qty / 1000)
    elif unit == "kg":
        cost = unit_price * qty
    elif unit == "ml":
        cost = unit_price * (qty / 1000)
    elif unit in ("l", "litre", "liter"):
        cost = unit_price * qty
    else:
        cost = unit_price * qty

    return round(max(cost, 1), 2)

async def _add_items_to_inventory(db, user_id: str, items: list[dict]) -> list[str]:
    """Single responsibility: inventory write only."""
    now = datetime.utcnow()
    docs = [
        {
            "user_id": user_id,
            "name": item.get("name") or item.get("item"),
            "quantity": _quantity_number(item.get("quantity") or item.get("suggested_qty"), 1),
            "unit": _unit_for(item),
            "cost_per_unit": _item_total(item),
            "status": "fresh",
            "purchase_date": now,
            "expiry_date": now + timedelta(days=30),
            "store": "AI Order (Simulated)",
            "category": item.get("category", "PANTRY_DRY"),
            "created_at": now,
        }
        for item in items
    ]
    result = await db.inventory.insert_many(docs)
    return [str(i) for i in result.inserted_ids]

async def _record_purchase_in_ledger(db, user_id: str, items: list[dict]) -> str:
    """Single responsibility: financial write only."""
    total = round(sum(_item_total(i) for i in items), 2)
    now = datetime.utcnow()
    result = await db.financial_ledger.insert_one({
        "user_id": user_id,
        "type": "expense",
        "amount": total,
        "category": "Groceries",
        "date": now,
        "created_at": now,
        "description": f"AI-ordered: {', '.join((i.get('name') or i.get('item') or 'item') for i in items)}",
        "items_summary": [
            {
                "name": i.get("name") or i.get("item"),
                "quantity": i.get("quantity") or i.get("suggested_qty") or 1,
                "unit": _unit_for(i),
                "estimated_cost": _item_total(i),
            }
            for i in items
        ],
        "source": "ai_ordering",
    })
    return str(result.inserted_id)

async def simulate_platform_order(db, user_id: str, items: list[dict]) -> dict:
    """Orchestrator — runs both writes in parallel, returns structured result."""
    try:
        normalized_items = [
            {**item, "name": item.get("name") or item.get("item") or "Ingredient"}
            for item in items
        ]
        inv_ids, ledger_id = await asyncio.gather(
            _add_items_to_inventory(db, user_id, normalized_items),
            _record_purchase_in_ledger(db, user_id, normalized_items)
        )
        total = round(sum(_item_total(item) for item in normalized_items), 2)
        return {
            "success": True,
            "message": f"Ordered {len(normalized_items)} items for ₹{total:.0f}. Added to pantry and finance ledger.",
            "items_added": [i["name"] for i in normalized_items],
            "inventory_ids": inv_ids,
            "ledger_id": ledger_id,
            "total_amount": total,
            "currency": "INR",
            "provider": "AI Order (Simulated)"
        }
    except Exception as e:
        return {"success": False, "error": str(e), "items": items}
