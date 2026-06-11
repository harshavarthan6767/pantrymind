from datetime import datetime

async def run_monthly_budget_scan(user_id: str = "default_user") -> dict:
    """
    Checks if the user is on track with food budget.
    Triggered on the 20th of each month.
    """
    from services.db_service import get_db
    db  = await get_db()
    now = datetime.utcnow()

    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    result = await db.financial_ledger.aggregate([
        {"$match": {
            "type": "expense", "category": "groceries",
            "date": {"$gte": month_start.isoformat()}
        }},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]).to_list(1)

    spent   = result[0]["total"] if result else 0
    profile = await db.user_profile.find_one({}) or {}
    budget  = profile.get("monthly_food_budget", 5000)

    days_elapsed  = now.day
    projected     = (spent / days_elapsed * 30) if days_elapsed > 0 else 0
    overshoot_pct = (projected - budget) / budget * 100 if budget > 0 else 0

    if overshoot_pct > 10:
        alert = {
            "user_id":    user_id,
            "type":       "budget_alert",
            "title":      f"💸 Food spend projected to exceed budget by {overshoot_pct:.0f}%",
            "body":       (
                f"Spent ₹{spent:.0f} in {days_elapsed} days. "
                f"Projected: ₹{projected:.0f} vs budget ₹{budget:.0f}. "
                f"Ask for a budget-friendly meal plan or shopping list."
            ),
            "severity":   "warning",
            "items":      [],
            "read":       False,
            "created_at": now
        }
        await db.notifications.insert_one(alert)
        return {"budget_alert": True, "projected": projected, "budget": budget}

    return {"budget_alert": False, "projected": projected, "budget": budget}
