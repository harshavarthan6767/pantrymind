"""
Carbon Footprint Tools for PantryMind.

Wraps CarbonService for CO₂ lookups, per-receipt impact logging,
periodic summaries, and green-swap suggestions.
"""

import logging
from datetime import datetime, timedelta

from google.adk.tools import ToolContext

from services.carbon_service import CarbonService
from services.db_service import MongoDBService

logger = logging.getLogger("pantrymind.tools.carbon")

carbon_service = CarbonService()
db = MongoDBService()


async def lookup_carbon_footprint(
    item_name: str,
    tool_context: ToolContext,
) -> dict:
    """Look up the CO₂ equivalent emissions per kg for a food item.

    Call this tool when the user asks about the carbon footprint of a
    specific food, e.g. "how bad is beef for the environment?" or
    "what's the CO₂ of rice?".

    Args:
        item_name: Name of the food item.
        tool_context: ADK tool context.

    Returns:
        dict with keys: item_name, co2_per_kg, impact_level, source.
    """
    try:
        co2 = carbon_service.get_co2_per_kg(item_name)

        if co2 >= 20:
            level = "very_high"
        elif co2 >= 10:
            level = "high"
        elif co2 >= 5:
            level = "moderate"
        elif co2 >= 2:
            level = "low"
        else:
            level = "very_low"

        result = {
            "item_name": item_name,
            "co2_per_kg": co2,
            "impact_level": level,
            "source": "Our World in Data",
        }
        logger.info("Carbon lookup: %s → %.2f kg CO₂/kg (%s)", item_name, co2, level)
        return result

    except Exception as e:
        logger.error("Carbon lookup failed for '%s': %s", item_name, e, exc_info=True)
        return {"error": str(e), "item_name": item_name}


async def log_carbon_impact(
    receipt_id: str,
    items: list[dict],
    tool_context: ToolContext = None,
) -> dict:
    """Calculate and store CO₂ impact for all items in a receipt.

    Call this tool after a receipt is processed to record the carbon
    footprint of the entire purchase. Each item should have 'name' and
    'quantity_kg' keys.

    Args:
        receipt_id: The MongoDB _id of the receipt document.
        items: List of dicts with keys: name (str), quantity_kg (float).
        tool_context: ADK tool context.

    Returns:
        dict with keys: receipt_id, item_impacts (list), total_co2_kg,
        avg_impact_level.
    """
    try:
        item_impacts = []
        total_co2 = 0.0

        for item in items:
            name = item.get("name", "unknown")
            qty = float(item.get("quantity_kg", 0.5))
            impact = carbon_service.calculate_impact(name, qty)
            item_impacts.append(impact)
            total_co2 += impact.get("total_co2_kg", 0)

        # Classify overall impact
        avg_per_item = total_co2 / max(1, len(items))
        if avg_per_item >= 10:
            avg_level = "very_high"
        elif avg_per_item >= 5:
            avg_level = "high"
        elif avg_per_item >= 2:
            avg_level = "moderate"
        else:
            avg_level = "low"

        # Store in carbon_log
        log_doc = {
            "receipt_id": receipt_id,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "items": item_impacts,
            "total_co2_kg": round(total_co2, 2),
            "avg_impact_level": avg_level,
            "created_at": datetime.now().isoformat(),
        }
        await db.insert_one("carbon_log", log_doc)

        result = {
            "receipt_id": receipt_id,
            "item_impacts": item_impacts,
            "total_co2_kg": round(total_co2, 2),
            "avg_impact_level": avg_level,
        }

        logger.info(
            "Carbon impact logged: receipt=%s, total=%.2f kg CO₂",
            receipt_id, total_co2,
        )
        return result

    except Exception as e:
        logger.error("Carbon impact logging failed: %s", e, exc_info=True)
        return {"error": str(e), "receipt_id": receipt_id}


async def get_carbon_summary(
    period: str = "month",
    tool_context: ToolContext = None,
) -> dict:
    """Get aggregated carbon footprint summary for a period.

    Call this tool when the user asks "what's my carbon footprint this
    month?" or wants a sustainability overview.

    Args:
        period: One of 'week', 'month', 'year'. Determines lookback window.
        tool_context: ADK tool context.

    Returns:
        dict with keys: period, start_date, end_date, total_co2_kg,
        receipt_count, avg_co2_per_receipt, top_contributors (list).
    """
    try:
        now = datetime.now()
        period_days = {"week": 7, "month": 30, "year": 365}
        lookback = period_days.get(period, 30)
        start_date = (now - timedelta(days=lookback)).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")

        # Total CO₂ and count
        total_pipeline = [
            {"$match": {"date": {"$gte": start_date, "$lte": end_date}}},
            {"$group": {
                "_id": None,
                "total_co2": {"$sum": "$total_co2_kg"},
                "count": {"$sum": 1},
            }},
        ]
        totals = await db.aggregate("carbon_log", total_pipeline)

        total_co2 = 0.0
        receipt_count = 0
        if totals:
            total_co2 = totals[0].get("total_co2", 0)
            receipt_count = totals[0].get("count", 0)

        # Top contributors: unwind items and aggregate by item name
        top_pipeline = [
            {"$match": {"date": {"$gte": start_date, "$lte": end_date}}},
            {"$unwind": "$items"},
            {"$group": {
                "_id": "$items.item_name",
                "total_co2": {"$sum": "$items.total_co2_kg"},
                "total_qty_kg": {"$sum": "$items.quantity_kg"},
            }},
            {"$sort": {"total_co2": -1}},
            {"$limit": 5},
        ]
        top_items = await db.aggregate("carbon_log", top_pipeline)
        contributors = [
            {
                "item": t.get("_id", "unknown"),
                "total_co2_kg": round(t.get("total_co2", 0), 2),
                "total_qty_kg": round(t.get("total_qty_kg", 0), 2),
            }
            for t in top_items
        ]

        result = {
            "period": period,
            "start_date": start_date,
            "end_date": end_date,
            "total_co2_kg": round(total_co2, 2),
            "receipt_count": receipt_count,
            "avg_co2_per_receipt": round(
                total_co2 / max(1, receipt_count), 2
            ),
            "top_contributors": contributors,
        }

        logger.info(
            "Carbon summary: %s period, %.2f kg CO₂ total",
            period, total_co2,
        )
        return result

    except Exception as e:
        logger.error("Carbon summary failed: %s", e, exc_info=True)
        return {"error": str(e), "period": period}


async def suggest_green_swaps(
    item_name: str,
    tool_context: ToolContext = None,
) -> dict | None:
    """Suggest a lower-carbon alternative for a high-impact food item.

    Call this tool when the user asks for greener alternatives, or
    proactively after detecting a high-impact item in a receipt.
    Returns None if the item is already low-impact.

    Args:
        item_name: Food item to find a swap for.
        tool_context: ADK tool context.

    Returns:
        dict with current_item, current_co2, suggested_item, suggested_co2,
        savings_per_kg, reduction_pct — or None if already low-impact.
    """
    try:
        result = carbon_service.suggest_green_swap(item_name)
        if result:
            logger.info(
                "Green swap for '%s': %s (saves %.1f%% CO₂)",
                item_name,
                result.get("suggested_item"),
                result.get("reduction_pct", 0),
            )
        else:
            logger.info("No green swap needed for '%s' (already low-impact)", item_name)
        return result

    except Exception as e:
        logger.error("Green swap suggestion failed for '%s': %s", item_name, e, exc_info=True)
        return None
