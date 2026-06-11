import os
from datetime import datetime, timedelta


def _effective_user_id(user_id: str | None = None) -> str:
    return user_id or os.getenv("DEMO_USER_ID", "demo_user_001")


def _parse_iso_datetime(value: str | None, fallback: datetime) -> datetime:
    if not value:
        return fallback
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo:
            parsed = parsed.replace(tzinfo=None)
        return parsed
    except Exception:
        return fallback


def _normalize_unit(item: dict) -> str:
    unit = item.get("unit")
    if unit and str(unit).lower() != "none":
        return unit
    qty = item.get("quantity", 0)
    return "item" if qty == 1 else "items"


async def get_inventory_overview(user_id: str | None = None) -> dict:
    """Fast direct inventory summary for pantry, kitchen, shopping, and voice paths."""
    from adk.tools.smart_inventory import get_smart_inventory_context

    return await get_smart_inventory_context(_effective_user_id(user_id))


async def get_finance_overview(
    user_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Fast direct finance summary grouped by category for the requested period."""
    from services.db_service import get_db

    db = await get_db()
    now = datetime.utcnow()
    start = _parse_iso_datetime(start_date, now.replace(day=1, hour=0, minute=0, second=0, microsecond=0))
    end = _parse_iso_datetime(end_date, now)
    effective_user_id = _effective_user_id(user_id)

    rows = await db.financial_ledger.find({
        "user_id": effective_user_id,
        "type": "expense",
    }).sort("date", -1).limit(500).to_list(500)

    filtered = []
    for tx in rows:
        tx_date = _parse_iso_datetime(tx.get("date"), now) if isinstance(tx.get("date"), str) else tx.get("date")
        if not isinstance(tx_date, datetime):
            tx_date = _parse_iso_datetime(str(tx_date) if tx_date else None, now)
        if start <= tx_date <= end:
            filtered.append({**tx, "_parsed_date": tx_date})

    category_map: dict[str, dict] = {}
    for tx in filtered:
        category = tx.get("category") or "uncategorized"
        key = str(category)
        bucket = category_map.setdefault(key, {"_id": key, "total": 0, "count": 0})
        bucket["total"] += float(tx.get("amount") or 0)
        bucket["count"] += 1

    by_category = sorted(category_map.values(), key=lambda row: row.get("total", 0), reverse=True)
    grand_total = sum(row.get("total", 0) for row in by_category)
    recent = sorted(filtered, key=lambda tx: tx.get("_parsed_date", now), reverse=True)[:10]

    return {
        "user_id": effective_user_id,
        "start": start.isoformat() + "Z",
        "end": end.isoformat() + "Z",
        "total_expense": round(grand_total, 2),
        "by_category": [
            {
                "category": row.get("_id") or "uncategorized",
                "total": round(row.get("total", 0), 2),
                "count": row.get("count", 0),
            }
            for row in by_category
        ],
        "recent_transactions": [
            {
                "date": tx.get("date").isoformat() + "Z" if hasattr(tx.get("date"), "isoformat") else str(tx.get("date")),
                "amount": tx.get("amount", 0),
                "category": tx.get("category"),
                "description": tx.get("description") or tx.get("merchant") or tx.get("name"),
            }
            for tx in recent
        ],
    }


async def get_shopping_context(user_id: str | None = None) -> dict:
    """Fast direct shopping inputs: current inventory, profile, and current month grocery spend."""
    from services.db_service import get_db

    db = await get_db()
    effective_user_id = _effective_user_id(user_id)
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    inventory = await db.inventory.find({
        "user_id": effective_user_id,
        "is_consumed": {"$ne": True},
        "quantity": {"$gt": 0},
    }).sort("safe_expiry_date", 1).limit(200).to_list(200)

    profile = await db.user_profile.find_one({"user_id": effective_user_id}) or {}
    grocery_rows = await db.financial_ledger.find({
        "user_id": effective_user_id,
        "type": "expense",
        "category": {"$in": ["groceries", "grocery", "food", "Groceries", "Grocery", "Food"]},
    }).limit(500).to_list(500)

    spent = 0
    for tx in grocery_rows:
        tx_date = _parse_iso_datetime(tx.get("date"), now) if isinstance(tx.get("date"), str) else tx.get("date")
        if not isinstance(tx_date, datetime):
            tx_date = _parse_iso_datetime(str(tx_date) if tx_date else None, now)
        if month_start <= tx_date <= now:
            spent += float(tx.get("amount") or 0)

    monthly_budget = profile.get("monthly_food_budget") or profile.get("food_budget") or 5000

    return {
        "user_id": effective_user_id,
        "inventory": [
            {
                "name": item.get("name"),
                "normalized_name": item.get("normalized_name") or item.get("name"),
                "category": item.get("category"),
                "sub_category": item.get("sub_category"),
                "quantity": item.get("quantity", 0),
                "unit": _normalize_unit(item),
                "status": item.get("status"),
                "is_consumed": item.get("is_consumed", False),
            }
            for item in inventory
        ],
        "dietary_preference": profile.get("dietary_preference") or profile.get("dietary_pref") or "NON_VEG",
        "monthly_food_budget": monthly_budget,
        "spent_this_month": round(spent, 2),
        "remaining_budget": round(max(0, monthly_budget - spent), 2),
    }
