from datetime import datetime, timedelta

async def run_daily_expiry_scan(user_id: str = "default_user") -> dict:
    """
    Queries inventory for expiring/expired items and stores alerts
    in the notifications collection.

    Triggered daily at 08:00 IST (02:30 UTC) by Cloud Scheduler.
    """
    from services.db_service import get_db
    db  = await get_db()
    now = datetime.utcnow()

    expired  = await db.inventory.find({
        "is_consumed": False, "status": "Expired"
    }).to_list(None)

    expiring = await db.inventory.find({
        "is_consumed": False,
        "status": {"$in": ["Critical", "Expiring Soon"]},
        "safe_expiry_date": {"$lte": (now + timedelta(days=3)).isoformat()}
    }).to_list(None)

    alerts = []

    if expired:
        names = [i.get("normalized_name", i.get("name")) for i in expired[:5]]
        alerts.append({
            "user_id":    user_id,
            "type":       "expiry_alert",
            "title":      f"🚨 {len(expired)} items have expired",
            "body":       f"{', '.join(names)} should be removed or used immediately.",
            "severity":   "critical",
            "items":      names,
            "read":       False,
            "created_at": now
        })

    if expiring:
        names = [i.get("normalized_name", i.get("name")) for i in expiring[:5]]
        alerts.append({
            "user_id":    user_id,
            "type":       "expiry_alert",
            "title":      f"⚠️  {len(expiring)} items expiring within 3 days",
            "body":       f"{', '.join(names)} need to be used. Ask Chef Mira for meal ideas!",
            "severity":   "warning",
            "items":      names,
            "read":       False,
            "created_at": now
        })

    if len(expiring) + len(expired) >= 5:
        alerts.append({
            "user_id":    user_id,
            "type":       "meal_suggestion",
            "title":      "👨🍳 Chef Mira has ideas for your expiring items",
            "body":       f"Try: 'Plan a meal using expiring items' to reduce waste.",
            "severity":   "info",
            "items":      [],
            "read":       False,
            "created_at": now
        })

    if alerts:
        await db.notifications.insert_many(alerts)

    return {"alerts_generated": len(alerts), "expiring": len(expiring), "expired": len(expired)}
