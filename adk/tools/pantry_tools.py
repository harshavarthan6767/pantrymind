import asyncio
from datetime import datetime, timedelta

def calculate_expiry_for_item(item: dict) -> dict:
    return item

def get_status_badge(status: str) -> str:
    return status

def format_inventory_for_agent(inventory: list) -> str:
    return str(inventory)

async def get_expiring_items(db, user_id: str, days: int = 3) -> dict:
    cutoff = datetime.utcnow() + timedelta(days=days)
    items = await db.inventory.find({
        "user_id": user_id,
        "status": {"$ne": "consumed"},
        "expiry_date": {"$lte": cutoff, "$gte": datetime.utcnow()}
    }).sort("expiry_date", 1).to_list(50)

    return {
        "count": len(items),
        "items": [
            {
                "name": i["name"],
                "expires_in_days": max(0, (i["expiry_date"] - datetime.utcnow()).days),
                "quantity": i["quantity"],
                "unit": i["unit"]
            }
            for i in items
        ],
        "urgent": [i["name"] for i in items
                   if (i["expiry_date"] - datetime.utcnow()).days <= 1]
    }

async def mark_item_consumed(db, user_id: str, item_name: str,
                              quantity: float, unit: str) -> str:
    item = await db.inventory.find_one({
        "user_id": user_id,
        "name": {"$regex": item_name, "$options": "i"},
        "status": {"$ne": "consumed"}
    })
    if not item:
        return f"'{item_name}' not found in your pantry."

    new_qty = max(0, item["quantity"] - quantity)
    new_status = "consumed" if new_qty <= 0 else item["status"]

    await asyncio.gather(
        db.inventory.update_one(
            {"_id": item["_id"]},
            {"$set": {"quantity": new_qty, "status": new_status}}
        ),
        db.consumption_history.insert_one({
            "user_id": user_id,
            "item_id": item["_id"],
            "item_name": item["name"],
            "quantity_consumed": quantity,
            "unit": unit,
            "date": datetime.utcnow(),
            "reason": "consumed"
        })
    )
    return f"Marked {quantity}{unit} of '{item['name']}' as consumed. {new_qty}{unit} remaining."
