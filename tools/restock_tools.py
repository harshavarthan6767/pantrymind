"""
Smart Restock Tools for PantryMind.

Analyses consumption history to predict depletion dates and generate
proactive shopping lists.
"""

import logging
from datetime import datetime, timedelta

from google.adk.tools import ToolContext

from services.db_service import MongoDBService

logger = logging.getLogger("pantrymind.tools.restock")

db = MongoDBService()


async def calculate_consumption_rate(
    item_name: str,
    lookback_days: int = 90,
    tool_context: ToolContext = None,
) -> dict:
    """Calculate the average daily consumption rate for an item.

    Call this tool when you need to know how fast the user consumes a
    particular item. Uses the consumption_history collection to compute
    average daily usage over the lookback period.

    Args:
        item_name: Name of the item (e.g. 'rice', 'milk').
        lookback_days: Number of days of history to consider (default 90).
        tool_context: ADK tool context.

    Returns:
        dict with keys: item_name, daily_rate_kg, weekly_rate_kg,
        data_points, lookback_days, confidence.
    """
    try:
        cutoff = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

        # Aggregate total consumed quantity from consumption_history
        pipeline = [
            {"$match": {
                "item_name": {"$regex": item_name, "$options": "i"},
                "date": {"$gte": cutoff},
            }},
            {"$group": {
                "_id": "$item_name",
                "total_consumed_kg": {"$sum": "$quantity_kg"},
                "data_points": {"$sum": 1},
                "first_date": {"$min": "$date"},
                "last_date": {"$max": "$date"},
            }},
        ]
        results = await db.aggregate("consumption_history", pipeline)

        if not results:
            return {
                "item_name": item_name,
                "daily_rate_kg": 0.0,
                "weekly_rate_kg": 0.0,
                "data_points": 0,
                "lookback_days": lookback_days,
                "confidence": "none",
                "message": f"No consumption history found for '{item_name}'.",
            }

        data = results[0]
        total = data.get("total_consumed_kg", 0)
        points = data.get("data_points", 0)

        # Calculate actual span
        try:
            first_dt = datetime.strptime(data["first_date"], "%Y-%m-%d")
            last_dt = datetime.strptime(data["last_date"], "%Y-%m-%d")
            actual_days = max(1, (last_dt - first_dt).days)
        except (ValueError, KeyError):
            actual_days = lookback_days

        daily_rate = total / actual_days
        weekly_rate = daily_rate * 7

        # Confidence based on data points
        if points >= 20:
            confidence = "high"
        elif points >= 5:
            confidence = "medium"
        else:
            confidence = "low"

        result = {
            "item_name": item_name,
            "daily_rate_kg": round(daily_rate, 4),
            "weekly_rate_kg": round(weekly_rate, 3),
            "total_consumed_kg": round(total, 3),
            "data_points": points,
            "actual_days": actual_days,
            "lookback_days": lookback_days,
            "confidence": confidence,
        }

        logger.info(
            "Consumption rate: %s → %.4f kg/day (%s confidence, %d points)",
            item_name, daily_rate, confidence, points,
        )
        return result

    except Exception as e:
        logger.error("Consumption rate failed for '%s': %s", item_name, e, exc_info=True)
        return {"error": str(e), "item_name": item_name}


async def predict_depletion(
    item_name: str,
    current_qty: float,
    tool_context: ToolContext = None,
) -> dict:
    """Predict when an inventory item will be depleted.

    Call this tool when the user asks "when will I run out of X?" or
    when generating restock alerts. Uses the consumption rate to
    estimate the depletion date.

    Args:
        item_name: Name of the item.
        current_qty: Current quantity on hand in kg.
        tool_context: ADK tool context.

    Returns:
        dict with keys: item_name, current_qty_kg, daily_rate_kg,
        predicted_empty_date, days_until_empty, confidence.
    """
    try:
        rate_data = await calculate_consumption_rate(item_name, 90, tool_context)

        daily_rate = rate_data.get("daily_rate_kg", 0)

        if daily_rate <= 0:
            return {
                "item_name": item_name,
                "current_qty_kg": current_qty,
                "daily_rate_kg": 0.0,
                "predicted_empty_date": None,
                "days_until_empty": None,
                "confidence": "none",
                "message": "Cannot predict — no consumption history available.",
            }

        days_left = current_qty / daily_rate
        empty_date = datetime.now() + timedelta(days=days_left)

        result = {
            "item_name": item_name,
            "current_qty_kg": current_qty,
            "daily_rate_kg": round(daily_rate, 4),
            "predicted_empty_date": empty_date.strftime("%Y-%m-%d"),
            "days_until_empty": round(days_left, 1),
            "confidence": rate_data.get("confidence", "low"),
        }

        logger.info(
            "Depletion prediction: %s → empty by %s (%.1f days)",
            item_name, result["predicted_empty_date"], days_left,
        )
        return result

    except Exception as e:
        logger.error("Depletion prediction failed for '%s': %s", item_name, e, exc_info=True)
        return {"error": str(e), "item_name": item_name}


async def update_restock_prediction(
    item_name: str,
    tool_context: ToolContext = None,
) -> dict:
    """Recalculate and upsert restock prediction for an item.

    Call this tool to refresh the restock prediction after a consumption
    event or inventory update. It fetches current inventory, calculates
    rate, predicts depletion, and upserts into restock_predictions.

    Args:
        item_name: Name of the item.
        tool_context: ADK tool context.

    Returns:
        dict with the updated prediction record.
    """
    try:
        # Get current inventory qty
        inv_items = await db.find(
            "inventory",
            query={"item_name": {"$regex": item_name, "$options": "i"}},
            limit=1,
        )

        if not inv_items:
            return {
                "item_name": item_name,
                "message": "Item not found in inventory.",
            }

        current_qty = float(inv_items[0].get("quantity_kg", inv_items[0].get("quantity", 0)))

        # Get prediction
        prediction = await predict_depletion(item_name, current_qty, tool_context)

        if "error" in prediction:
            return prediction

        # Upsert into restock_predictions
        upsert_doc = {
            "$set": {
                "item_name": item_name,
                "current_qty_kg": current_qty,
                "daily_rate_kg": prediction.get("daily_rate_kg", 0),
                "predicted_empty_date": prediction.get("predicted_empty_date"),
                "days_until_empty": prediction.get("days_until_empty"),
                "confidence": prediction.get("confidence", "low"),
                "updated_at": datetime.now().isoformat(),
            }
        }

        await db.update_one(
            "restock_predictions",
            query={"item_name": {"$regex": f"^{item_name}$", "$options": "i"}},
            update=upsert_doc,
            upsert=True,
        )

        logger.info("Restock prediction updated for '%s'", item_name)
        return {
            "item_name": item_name,
            "status": "updated",
            **prediction,
        }

    except Exception as e:
        logger.error("Restock prediction update failed for '%s': %s", item_name, e, exc_info=True)
        return {"error": str(e), "item_name": item_name}


async def get_restock_alerts(
    days_ahead: int = 3,
    tool_context: ToolContext = None,
) -> list[dict]:
    """Get items predicted to run out within N days.

    Call this tool when the user asks "what do I need to buy?" or
    "what's running low?" or for proactive restock alerts.

    Args:
        days_ahead: Number of days to look ahead (default 3).
        tool_context: ADK tool context.

    Returns:
        list of dicts: [{item_name, current_qty_kg, predicted_empty_date,
        days_until_empty, confidence}, ...].
    """
    try:
        cutoff = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")

        results = await db.find(
            "restock_predictions",
            query={
                "predicted_empty_date": {"$gte": today, "$lte": cutoff},
            },
            sort=[("predicted_empty_date", 1)],
            limit=50,
        )

        alerts = []
        for doc in results:
            alerts.append({
                "item_name": doc.get("item_name", ""),
                "current_qty_kg": doc.get("current_qty_kg", 0),
                "predicted_empty_date": doc.get("predicted_empty_date", ""),
                "days_until_empty": doc.get("days_until_empty", 0),
                "confidence": doc.get("confidence", "low"),
            })

        logger.info("Restock alerts: %d items depleting within %d days", len(alerts), days_ahead)
        return alerts

    except Exception as e:
        logger.error("Restock alerts query failed: %s", e, exc_info=True)
        return []


async def generate_shopping_list(
    tool_context: ToolContext = None,
) -> list[dict]:
    """Generate a shopping list of items predicted to run out within 7 days.

    Call this tool when the user asks for a shopping list, grocery list,
    or "what should I buy this week?". Returns all items from
    restock_predictions that are predicted to deplete in the next 7 days,
    along with suggested purchase quantities.

    Args:
        tool_context: ADK tool context.

    Returns:
        list of dicts: [{item_name, current_qty_kg, days_until_empty,
        suggested_buy_kg, estimated_weekly_need_kg}, ...].
    """
    try:
        cutoff = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")

        results = await db.find(
            "restock_predictions",
            query={
                "predicted_empty_date": {"$gte": today, "$lte": cutoff},
            },
            sort=[("predicted_empty_date", 1)],
            limit=100,
        )

        shopping_list = []
        for doc in results:
            daily_rate = doc.get("daily_rate_kg", 0)
            weekly_need = round(daily_rate * 7, 3)
            current = doc.get("current_qty_kg", 0)
            # Suggest buying at least a week's worth
            suggested = max(0, round(weekly_need - current, 3))

            shopping_list.append({
                "item_name": doc.get("item_name", ""),
                "current_qty_kg": current,
                "days_until_empty": doc.get("days_until_empty", 0),
                "daily_rate_kg": round(daily_rate, 4),
                "estimated_weekly_need_kg": weekly_need,
                "suggested_buy_kg": suggested,
            })

        logger.info("Shopping list generated: %d items", len(shopping_list))
        return shopping_list

    except Exception as e:
        logger.error("Shopping list generation failed: %s", e, exc_info=True)
        return []
