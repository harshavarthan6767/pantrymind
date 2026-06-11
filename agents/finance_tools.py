from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from bson import ObjectId

async def query_ledger(
    db,
    user_id: str,
    start_date: str = None,   # ISO format or natural: "this month", "last 30 days"
    end_date: str = None,
    category: str = None      # "groceries", "household", "personal_care", etc.
) -> dict:
    """
    Primary finance tool. Returns all ledger entries in a date range.
    The agent MUST call this before answering any expense question.
    """
    start, end = _parse_date_range(start_date, end_date)

    match = {
        "user_id": ObjectId(user_id) if user_id else None,
        "type": "expense",
        "date": {"$gte": start, "$lte": end}
    }
    if not match["user_id"]:
        del match["user_id"] # Handle mock/dev scenarios without auth
        
    if category:
        match["category"] = category

    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": "$category",
            "total":        {"$sum": "$amount"},
            "count":        {"$sum": 1},
            "latest_date":  {"$max": "$date"},
            "entries": {
                "$push": {
                    "amount":      "$amount",
                    "date":        "$date",
                    "description": "$description",
                    "receipt_id":  {"$toString": "$receipt_id"}
                }
            }
        }},
        {"$sort": {"total": -1}}
    ]

    results = await db.financial_ledger.aggregate(pipeline).to_list(None)

    grand_total = sum(r["total"] for r in results)

    return {
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "grand_total": round(grand_total, 2),
        "by_category": [
            {
                "category":    r["_id"],
                "total":       round(r["total"], 2),
                "pct_of_spend":round((r["total"] / grand_total * 100) if grand_total else 0, 1),
                "num_transactions": r["count"]
            }
            for r in results
        ],
        "num_transactions": sum(r["count"] for r in results)
    }

async def get_budget_summary(db, user_id: str) -> dict:
    """
    Returns salary, total spend this month, and disposable income.
    """
    # Assuming user_profile contains finance settings for now
    query = {"user_id": ObjectId(user_id)} if user_id else {}
    profile = await db.user_finance_profiles.find_one(query)
    monthly_salary = profile.get("monthly_salary", 0) if profile else 0

    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_data = await query_ledger(db, user_id, month_start.isoformat(), now.isoformat())

    spent_this_month = month_data["grand_total"]
    disposable = monthly_salary - spent_this_month

    return {
        "monthly_salary":       round(monthly_salary, 2),
        "spent_this_month":     round(spent_this_month, 2),
        "disposable_income":    round(disposable, 2),
        "spend_rate_pct":       round((spent_this_month / monthly_salary * 100) if monthly_salary else 0, 1),
        "days_left_in_month":   (month_start + relativedelta(months=1) - now).days
    }

async def compare_months(db, user_id: str, months_back: int = 1) -> dict:
    """
    Compares current month spend to N months ago.
    """
    now = datetime.utcnow()
    this_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_start = this_start - relativedelta(months=months_back)
    prev_end   = this_start - timedelta(seconds=1)

    this_data = await query_ledger(db, user_id, this_start.isoformat(), now.isoformat())
    prev_data  = await query_ledger(db, user_id, prev_start.isoformat(), prev_end.isoformat())

    delta = this_data["grand_total"] - prev_data["grand_total"]
    delta_pct = (delta / prev_data["grand_total"] * 100) if prev_data["grand_total"] else 0

    return {
        "this_month":      {"total": round(this_data["grand_total"], 2), "period": this_start.strftime("%B %Y")},
        "previous_month":  {"total": round(prev_data["grand_total"], 2), "period": prev_start.strftime("%B %Y")},
        "change_amount":   round(delta, 2),
        "change_pct":      round(delta_pct, 1),
        "trend":           "up" if delta > 0 else "down" if delta < 0 else "flat"
    }

def _parse_date_range(start_date, end_date):
    """Parse natural language or ISO dates."""
    now = datetime.utcnow()
    if not start_date or start_date == "this month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end   = now
    elif start_date == "last month":
        start = (now.replace(day=1) - relativedelta(months=1)).replace(hour=0, minute=0, second=0)
        end   = now.replace(day=1, hour=0, minute=0, second=0) - timedelta(seconds=1)
    elif start_date == "last 30 days":
        start = now - timedelta(days=30)
        end   = now
    elif start_date == "last 7 days":
        start = now - timedelta(days=7)
        end   = now
    else:
        try:
            start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        except:
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        try:
            end = datetime.fromisoformat(end_date.replace("Z", "+00:00")) if end_date else now
        except:
            end = now
    return start, end
