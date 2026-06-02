"""
Warranty Tracker Tools for PantryMind.

CRUD operations for product warranties stored in MongoDB.
Supports adding warranties, checking expiring warranties, and alerting.
"""

import logging
from datetime import datetime, timedelta

from google.adk.tools import ToolContext

from services.db_service import MongoDBService

logger = logging.getLogger("pantrymind.tools.warranty")

db = MongoDBService()


async def add_warranty(
    item_name: str,
    purchase_date: str,
    warranty_months: int,
    gcs_invoice_uri: str = "",
    category: str = "electronics",
    tool_context: ToolContext = None,
) -> dict:
    """Add a new product warranty to the tracker.

    Call this tool when the user says they bought a new product with a
    warranty, or after an invoice is parsed that contains warranty info.
    Stores the warranty in MongoDB and calculates the expiry date.

    Args:
        item_name: Product name (e.g. 'Samsung Galaxy S24').
        purchase_date: Date of purchase (ISO YYYY-MM-DD).
        warranty_months: Warranty duration in months.
        gcs_invoice_uri: Optional GCS URI of the stored invoice image.
        category: Product category — one of 'electronics', 'appliances',
            'furniture', 'clothing', 'accessories', 'other'.
        tool_context: ADK tool context.

    Returns:
        dict with keys: warranty_id, item_name, purchase_date,
        warranty_months, expiry_date, category, status.
    """
    try:
        purchase_dt = datetime.strptime(purchase_date, "%Y-%m-%d")
        # Approximate month addition: 30 days per month
        expiry_dt = purchase_dt + timedelta(days=warranty_months * 30)

        doc = {
            "item_name": item_name,
            "purchase_date": purchase_date,
            "warranty_months": warranty_months,
            "expiry_date": expiry_dt.strftime("%Y-%m-%d"),
            "gcs_invoice_uri": gcs_invoice_uri,
            "category": category,
            "alerted": False,
            "created_at": datetime.now().isoformat(),
        }

        warranty_id = await db.insert_one("warranties", doc)

        result = {
            "warranty_id": warranty_id,
            "item_name": item_name,
            "purchase_date": purchase_date,
            "warranty_months": warranty_months,
            "expiry_date": expiry_dt.strftime("%Y-%m-%d"),
            "category": category,
            "status": "active",
        }

        logger.info(
            "Warranty added: %s, expires %s (id=%s)",
            item_name, result["expiry_date"], warranty_id,
        )
        return result

    except Exception as e:
        logger.error("Add warranty failed for '%s': %s", item_name, e, exc_info=True)
        return {"error": str(e), "item_name": item_name}


async def get_expiring_warranties(
    days_ahead: int = 30,
    tool_context: ToolContext = None,
) -> list[dict]:
    """Get warranties expiring within the next N days.

    Call this tool when the user asks about upcoming warranty expirations,
    or as part of periodic alerting. Shows warranties that will expire
    soon so the user can take action (claim, extend, etc.).

    Args:
        days_ahead: Number of days to look ahead (default 30).
        tool_context: ADK tool context.

    Returns:
        list of dicts, each with item_name, purchase_date, expiry_date,
        days_remaining, category, warranty_id.
    """
    try:
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        cutoff_str = (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

        results = await db.find(
            "warranties",
            query={
                "expiry_date": {"$gte": today_str, "$lte": cutoff_str},
            },
            sort=[("expiry_date", 1)],
            limit=50,
        )

        warranties = []
        for doc in results:
            exp_str = doc.get("expiry_date", "")
            try:
                exp_dt = datetime.strptime(exp_str, "%Y-%m-%d")
                days_left = (exp_dt - now).days
            except ValueError:
                days_left = -1

            warranties.append({
                "warranty_id": doc.get("_id", ""),
                "item_name": doc.get("item_name", ""),
                "purchase_date": doc.get("purchase_date", ""),
                "expiry_date": exp_str,
                "days_remaining": max(0, days_left),
                "category": doc.get("category", ""),
                "alerted": doc.get("alerted", False),
            })

        logger.info(
            "Found %d warranties expiring within %d days",
            len(warranties), days_ahead,
        )
        return warranties

    except Exception as e:
        logger.error("Expiring warranties query failed: %s", e, exc_info=True)
        return []


async def get_warranty_by_item(
    item_name: str,
    tool_context: ToolContext = None,
) -> dict | None:
    """Look up warranty details for a specific product.

    Call this tool when the user asks about the warranty status of a
    specific item (e.g. "is my laptop still under warranty?").

    Args:
        item_name: Product name to search for (case-insensitive substring).
        tool_context: ADK tool context.

    Returns:
        dict with warranty details, or None if no warranty found.
    """
    try:
        # Use regex for case-insensitive substring match
        results = await db.find(
            "warranties",
            query={
                "item_name": {"$regex": item_name, "$options": "i"},
            },
            sort=[("created_at", -1)],
            limit=1,
        )

        if not results:
            logger.info("No warranty found for '%s'", item_name)
            return None

        doc = results[0]
        now = datetime.now()
        exp_str = doc.get("expiry_date", "")

        try:
            exp_dt = datetime.strptime(exp_str, "%Y-%m-%d")
            days_left = (exp_dt - now).days
            status = "active" if days_left > 0 else "expired"
        except ValueError:
            days_left = -1
            status = "unknown"

        result = {
            "warranty_id": doc.get("_id", ""),
            "item_name": doc.get("item_name", ""),
            "purchase_date": doc.get("purchase_date", ""),
            "warranty_months": doc.get("warranty_months", 0),
            "expiry_date": exp_str,
            "days_remaining": max(0, days_left),
            "status": status,
            "category": doc.get("category", ""),
            "gcs_invoice_uri": doc.get("gcs_invoice_uri", ""),
        }

        logger.info("Warranty found for '%s': %s, %s", item_name, status, exp_str)
        return result

    except Exception as e:
        logger.error("Warranty lookup failed for '%s': %s", item_name, e, exc_info=True)
        return None


async def mark_warranty_alerted(
    warranty_id: str,
    tool_context: ToolContext = None,
) -> dict:
    """Mark a warranty as alerted (notification sent to user).

    Call this tool after successfully notifying the user about an
    expiring warranty, so the system doesn't re-alert on subsequent runs.

    Args:
        warranty_id: The MongoDB _id of the warranty document.
        tool_context: ADK tool context.

    Returns:
        dict with warranty_id and updated status.
    """
    try:
        from bson import ObjectId

        modified = await db.update_one(
            "warranties",
            query={"_id": ObjectId(warranty_id)},
            update={"$set": {"alerted": True, "alerted_at": datetime.now().isoformat()}},
        )

        result = {
            "warranty_id": warranty_id,
            "alerted": True,
            "modified_count": modified,
        }

        logger.info("Warranty %s marked as alerted", warranty_id)
        return result

    except Exception as e:
        logger.error("Mark warranty alerted failed: %s", e, exc_info=True)
        return {"error": str(e), "warranty_id": warranty_id}
