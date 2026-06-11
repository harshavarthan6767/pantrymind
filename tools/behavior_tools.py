"""
Behavior Insights Tools for PantryMind.

MongoDB aggregation pipelines for spending analysis by day-of-week, category,
merchant, and month-over-month trends. Includes Gemini-powered natural-
language insight generation.
"""

import logging
from datetime import datetime, timedelta

from google.adk.tools import ToolContext

from services.db_service import MongoDBService

logger = logging.getLogger("pantrymind.tools.behavior")

db = MongoDBService()


async def generate_weekly_snapshot(
    tool_context: ToolContext = None,
) -> dict:
    """Generate a comprehensive weekly spending behaviour snapshot.

    Call this tool at the end of each week (or on-demand) to produce a
    full behaviour report. It runs MongoDB aggregation pipelines across
    the financial_ledger to summarise spending by day-of-week, category,
    and merchant for the last 7 days.

    Args:
        tool_context: ADK tool context.

    Returns:
        dict with keys: week_start, week_end, total_spent, by_day_of_week,
        by_category, top_merchants, transaction_count.
    """
    try:
        now = datetime.now()
        week_start = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        week_end = now.strftime("%Y-%m-%d")

        # ── Spending by day-of-week ────────────────────────────────────
        day_pipeline = [
            {"$match": {"date": {"$gte": week_start, "$lte": week_end}}},
            {"$addFields": {
                "date_parsed": {"$dateFromString": {"dateString": "$date"}},
            }},
            {"$group": {
                "_id": {"$dayOfWeek": "$date_parsed"},
                "total": {"$sum": "$amount"},
                "count": {"$sum": 1},
            }},
            {"$sort": {"_id": 1}},
        ]
        by_day = await db.aggregate("financial_ledger", day_pipeline)

        day_names = {1: "Sun", 2: "Mon", 3: "Tue", 4: "Wed", 5: "Thu", 6: "Fri", 7: "Sat"}
        by_day_named = [
            {
                "day": day_names.get(d.get("_id", 0), "?"),
                "total_spent": round(d.get("total", 0), 2),
                "transactions": d.get("count", 0),
            }
            for d in by_day
        ]

        # ── Spending by category ───────────────────────────────────────
        cat_pipeline = [
            {"$match": {"date": {"$gte": week_start, "$lte": week_end}}},
            {"$group": {
                "_id": "$category",
                "total": {"$sum": "$amount"},
                "count": {"$sum": 1},
            }},
            {"$sort": {"total": -1}},
        ]
        by_category = await db.aggregate("financial_ledger", cat_pipeline)
        by_category_list = [
            {
                "category": c.get("_id", "uncategorised"),
                "total_spent": round(c.get("total", 0), 2),
                "transactions": c.get("count", 0),
            }
            for c in by_category
        ]

        # ── Top merchants ─────────────────────────────────────────────
        merch_pipeline = [
            {"$match": {"date": {"$gte": week_start, "$lte": week_end}}},
            {"$group": {
                "_id": "$merchant",
                "total": {"$sum": "$amount"},
                "count": {"$sum": 1},
            }},
            {"$sort": {"total": -1}},
            {"$limit": 5},
        ]
        top_merchants = await db.aggregate("financial_ledger", merch_pipeline)
        top_merchants_list = [
            {
                "merchant": m.get("_id", "unknown"),
                "total_spent": round(m.get("total", 0), 2),
                "transactions": m.get("count", 0),
            }
            for m in top_merchants
        ]

        # ── Total ──────────────────────────────────────────────────────
        total_spent = sum(d["total_spent"] for d in by_day_named)
        total_txns = sum(d["transactions"] for d in by_day_named)

        snapshot = {
            "week_start": week_start,
            "week_end": week_end,
            "total_spent": round(total_spent, 2),
            "transaction_count": total_txns,
            "by_day_of_week": by_day_named,
            "by_category": by_category_list,
            "top_merchants": top_merchants_list,
        }

        # Persist snapshot
        snapshot_doc = {**snapshot, "created_at": now.isoformat()}
        await db.insert_one("behavior_snapshots", snapshot_doc)

        logger.info(
            "Weekly snapshot generated: ₹%.2f across %d transactions",
            total_spent, total_txns,
        )
        return snapshot

    except Exception as e:
        logger.error("Weekly snapshot generation failed: %s", e, exc_info=True)
        return {"error": str(e)}


async def get_spending_by_day_of_week(
    days: int = 30,
    tool_context: ToolContext = None,
) -> list[dict]:
    """Get average spending grouped by day of the week.

    Call this tool when the user asks about their spending patterns,
    e.g. "do I spend more on weekends?" or "which day do I shop most?".

    Args:
        days: Lookback period in days (default 30).
        tool_context: ADK tool context.

    Returns:
        list of dicts: [{day, avg_spent, total_spent, transactions}, ...].
    """
    try:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        pipeline = [
            {"$match": {"date": {"$gte": cutoff}}},
            {"$addFields": {
                "date_parsed": {"$dateFromString": {"dateString": "$date"}},
            }},
            {"$group": {
                "_id": {"$dayOfWeek": "$date_parsed"},
                "total": {"$sum": "$amount"},
                "count": {"$sum": 1},
            }},
            {"$sort": {"_id": 1}},
        ]
        results = await db.aggregate("financial_ledger", pipeline)

        day_names = {1: "Sun", 2: "Mon", 3: "Tue", 4: "Wed", 5: "Thu", 6: "Fri", 7: "Sat"}
        weeks_in_period = max(1, days / 7)

        output = [
            {
                "day": day_names.get(r.get("_id", 0), "?"),
                "avg_spent": round(r.get("total", 0) / weeks_in_period, 2),
                "total_spent": round(r.get("total", 0), 2),
                "transactions": r.get("count", 0),
            }
            for r in results
        ]

        logger.info("Spending by day-of-week: %d day lookback", days)
        return output

    except Exception as e:
        logger.error("Spending by day-of-week failed: %s", e, exc_info=True)
        return []


async def get_category_trend(
    months: int = 3,
    tool_context: ToolContext = None,
) -> list[dict]:
    """Get month-over-month spending trends by category.

    Call this tool when the user asks about category spending changes
    over time, e.g. "am I spending more on food lately?".

    Args:
        months: Number of months to look back (default 3).
        tool_context: ADK tool context.

    Returns:
        list of dicts: [{category, month, total_spent}, ...] sorted by
        category then month.
    """
    try:
        cutoff = (datetime.now() - timedelta(days=months * 30)).strftime("%Y-%m-%d")

        pipeline = [
            {"$match": {"date": {"$gte": cutoff}}},
            {"$addFields": {
                "month_key": {"$substr": ["$date", 0, 7]},  # "YYYY-MM"
            }},
            {"$group": {
                "_id": {"category": "$category", "month": "$month_key"},
                "total": {"$sum": "$amount"},
            }},
            {"$sort": {"_id.category": 1, "_id.month": 1}},
        ]
        results = await db.aggregate("financial_ledger", pipeline)

        output = [
            {
                "category": r["_id"]["category"],
                "month": r["_id"]["month"],
                "total_spent": round(r.get("total", 0), 2),
            }
            for r in results
        ]

        logger.info("Category trend: %d months, %d data points", months, len(output))
        return output

    except Exception as e:
        logger.error("Category trend query failed: %s", e, exc_info=True)
        return []


async def get_top_merchants(
    limit: int = 5,
    tool_context: ToolContext = None,
) -> list[dict]:
    """Get the top merchants by total spending.

    Call this tool when the user asks "where do I shop the most?" or
    "who are my biggest vendors?".

    Args:
        limit: Number of top merchants to return (default 5).
        tool_context: ADK tool context.

    Returns:
        list of dicts: [{merchant, total_spent, transactions, avg_per_visit}, ...].
    """
    try:
        pipeline = [
            {"$group": {
                "_id": "$merchant",
                "total": {"$sum": "$amount"},
                "count": {"$sum": 1},
            }},
            {"$sort": {"total": -1}},
            {"$limit": limit},
        ]
        results = await db.aggregate("financial_ledger", pipeline)

        output = [
            {
                "merchant": r.get("_id", "unknown"),
                "total_spent": round(r.get("total", 0), 2),
                "transactions": r.get("count", 0),
                "avg_per_visit": round(
                    r.get("total", 0) / max(1, r.get("count", 1)), 2
                ),
            }
            for r in results
        ]

        logger.info("Top %d merchants retrieved", len(output))
        return output

    except Exception as e:
        logger.error("Top merchants query failed: %s", e, exc_info=True)
        return []


async def generate_insights_report(
    snapshot: dict,
    tool_context: ToolContext = None,
) -> str:
    """Generate a natural-language insights report from a behaviour snapshot.

    Call this tool after generate_weekly_snapshot to produce a human-readable
    summary. Uses the Gemini model (via ADK tool_context) to generate
    narrative insights from the raw data.

    Args:
        snapshot: The dict returned by generate_weekly_snapshot.
        tool_context: ADK tool context (used to access Gemini model).

    Returns:
        str — a multi-paragraph natural-language report with actionable insights.
    """
    try:
        import google.generativeai as genai

        prompt = f"""You are a personal finance analyst for PantryMind.
Analyse this weekly spending snapshot and provide concise, actionable insights
in 3-5 bullet points. Highlight unusual patterns, suggest savings, and note
positive trends.

Snapshot data:
- Period: {snapshot.get('week_start')} to {snapshot.get('week_end')}
- Total spent: ₹{snapshot.get('total_spent', 0):.2f}
- Transactions: {snapshot.get('transaction_count', 0)}
- By day: {snapshot.get('by_day_of_week', [])}
- By category: {snapshot.get('by_category', [])}
- Top merchants: {snapshot.get('top_merchants', [])}

Keep the tone friendly and the currency in INR (₹)."""

        model = genai.GenerativeModel("gemini-3.1-pro")
        response = model.generate_content(prompt)
        report = response.text

        logger.info("Insights report generated (%d chars)", len(report))
        return report

    except Exception as e:
        logger.error("Insights report generation failed: %s", e, exc_info=True)
        # Fallback: simple template-based report
        return (
            f"Weekly Spending Summary ({snapshot.get('week_start')} – "
            f"{snapshot.get('week_end')})\n"
            f"Total: ₹{snapshot.get('total_spent', 0):.2f} across "
            f"{snapshot.get('transaction_count', 0)} transactions.\n"
            f"Top category: {snapshot.get('by_category', [{}])[0].get('category', 'N/A') if snapshot.get('by_category') else 'N/A'}\n"
            f"(Detailed AI insights unavailable — see raw data above.)"
        )
