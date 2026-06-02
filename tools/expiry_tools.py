"""
Expiry / Shelf-Life Tools for PantryMind.

Wraps ExpiryService for fresh-produce shelf-life lookups, expiry prediction,
packed-goods suggested usage, and near-expiry inventory alerts from MongoDB.
"""

import logging
from datetime import datetime, timedelta

from google.adk.tools import ToolContext

from services.expiry_service import ExpiryService
from services.db_service import MongoDBService

logger = logging.getLogger("pantrymind.tools.expiry")

expiry_service = ExpiryService()
db = MongoDBService()


async def lookup_shelf_life(
    item_name: str,
    tool_context: ToolContext,
) -> dict:
    """Look up the expected shelf life (in days) of a food item.

    Call this tool when the user asks how long a specific food item
    lasts, or when you need shelf-life data for expiry calculations.
    Uses the USDA FoodKeeper knowledge base.

    Args:
        item_name: Name of the food item (e.g. 'apples', 'chicken breast').
        tool_context: ADK tool context.

    Returns:
        dict with keys: item_name, shelf_life_days, source.
    """
    try:
        days = expiry_service.get_shelf_life(item_name)
        result = {
            "item_name": item_name,
            "shelf_life_days": days,
            "source": "USDA FoodKeeper",
        }
        logger.info("Shelf life lookup: %s → %d days", item_name, days)
        return result
    except Exception as e:
        logger.error("Shelf life lookup failed for '%s': %s", item_name, e, exc_info=True)
        return {"error": str(e), "item_name": item_name}


async def calculate_expiry(
    item_name: str,
    purchase_date: str,
    tool_context: ToolContext,
) -> dict:
    """Predict the expiry date for a fresh produce item.

    Call this tool when the user adds fresh produce to inventory or asks
    when something will expire. Uses the formula:
        predicted_expiry = purchase_date + shelf_life_days

    Args:
        item_name: Name of the food item.
        purchase_date: ISO date string (YYYY-MM-DD) when the item was bought.
        tool_context: ADK tool context.

    Returns:
        dict with keys: item_name, purchase_date, shelf_life_days,
        predicted_expiry, storage_method, days_remaining, source.
    """
    try:
        result = expiry_service.predict_expiry_fresh(item_name, purchase_date)
        # Add days_remaining for convenience
        expiry_dt = datetime.strptime(result["predicted_expiry"], "%Y-%m-%d")
        result["days_remaining"] = max(0, (expiry_dt - datetime.now()).days)
        logger.info(
            "Expiry prediction: %s → %s (%d days remaining)",
            item_name, result["predicted_expiry"], result["days_remaining"],
        )
        return result
    except Exception as e:
        logger.error("Expiry calculation failed for '%s': %s", item_name, e, exc_info=True)
        return {"error": str(e), "item_name": item_name}


async def calculate_suggested_usage(
    item_name: str,
    mfg_date: str,
    expiry_date: str,
    tool_context: ToolContext,
) -> dict:
    """Calculate the suggested usage date for a packed/packaged product.

    Call this tool when the user adds a packed grocery item with a
    manufacturing and expiry date printed on it. Uses the formula:
        suggested_use_by = expiry - (expiry - mfg) × 0.20
    This means: consume at 80 % of total shelf life for peak freshness.

    Args:
        item_name: Product name (e.g. 'Dairy Milk Chocolate').
        mfg_date: Manufacturing date (ISO YYYY-MM-DD).
        expiry_date: Printed expiry date (ISO YYYY-MM-DD).
        tool_context: ADK tool context.

    Returns:
        dict with keys: item_name, manufacture_date, expiry_date,
        total_shelf_days, suggested_use_by, days_until_suggested,
        recommendation.
    """
    try:
        result = expiry_service.calculate_suggested_usage_packed(
            item_name, mfg_date, expiry_date
        )
        logger.info(
            "Suggested usage: %s → use by %s",
            item_name, result.get("suggested_use_by"),
        )
        return result
    except Exception as e:
        logger.error(
            "Suggested usage calculation failed for '%s': %s",
            item_name, e, exc_info=True,
        )
        return {"error": str(e), "item_name": item_name}


async def get_expiring_soon(
    days_threshold: int = 3,
    tool_context: ToolContext = None,
) -> list[dict]:
    """Get inventory items that are expiring within the given threshold.

    Call this tool when the user asks "what's about to expire?",
    "any food going bad?", or needs alerts for near-expiry items.
    Queries the inventory collection in MongoDB for items whose
    predicted_expiry is within `days_threshold` days from today.

    Args:
        days_threshold: Number of days to look ahead (default 3).
        tool_context: ADK tool context.

    Returns:
        list of dicts, each with item_name, predicted_expiry,
        days_remaining, category, quantity.
    """
    try:
        now = datetime.now()
        cutoff = (now + timedelta(days=days_threshold)).strftime("%Y-%m-%d")
        today_str = now.strftime("%Y-%m-%d")

        # Query inventory for items with predicted_expiry between today and cutoff
        results = await db.find(
            "inventory",
            query={
                "predicted_expiry": {"$gte": today_str, "$lte": cutoff},
            },
            sort=[("predicted_expiry", 1)],
            limit=50,
        )

        expiring = []
        for doc in results:
            exp_str = doc.get("predicted_expiry", "")
            try:
                exp_dt = datetime.strptime(exp_str, "%Y-%m-%d")
                days_left = (exp_dt - now).days
            except ValueError:
                days_left = -1

            expiring.append({
                "item_name": doc.get("item_name", "unknown"),
                "predicted_expiry": exp_str,
                "days_remaining": max(0, days_left),
                "category": doc.get("category", ""),
                "quantity": doc.get("quantity", 0),
                "quantity_unit": doc.get("quantity_unit", ""),
            })

        logger.info(
            "Found %d items expiring within %d days",
            len(expiring), days_threshold,
        )
        return expiring

    except Exception as e:
        logger.error("Expiring-soon query failed: %s", e, exc_info=True)
        return []
