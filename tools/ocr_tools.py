"""
Document AI OCR Tools for PantryMind.

Wraps the OCRService to provide receipt/invoice parsing, data normalisation,
and item categorisation as Google ADK FunctionTools.
"""

import logging
import re
from datetime import datetime

from google.adk.tools import ToolContext

from services.ocr_service import OCRService

logger = logging.getLogger("pantrymind.tools.ocr")

ocr_service = OCRService()

# ── Category keyword mappings ──────────────────────────────────────────────
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "food": [
        "rice", "wheat", "flour", "atta", "dal", "lentil", "oil", "ghee",
        "butter", "milk", "curd", "paneer", "cheese", "bread", "egg",
        "chicken", "mutton", "fish", "prawn", "apple", "banana", "mango",
        "onion", "tomato", "potato", "sugar", "salt", "spice", "masala",
        "tea", "coffee", "juice", "biscuit", "chocolate", "chips", "noodle",
        "pasta", "cereal", "oats", "honey", "jam", "sauce", "ketchup",
        "fruit", "vegetable", "meat", "snack", "frozen", "yogurt",
    ],
    "clothing": [
        "shirt", "pant", "jeans", "kurta", "saree", "dress", "jacket",
        "sweater", "sock", "shoe", "sandal", "slipper", "cap", "hat",
        "scarf", "belt", "underwear", "t-shirt", "trouser", "skirt",
    ],
    "electronics": [
        "phone", "mobile", "laptop", "charger", "cable", "earphone",
        "headphone", "speaker", "mouse", "keyboard", "monitor", "tv",
        "television", "camera", "battery", "adapter", "usb", "hdmi",
        "tablet", "watch", "smartwatch", "printer", "router", "modem",
    ],
    "accessories": [
        "bag", "wallet", "purse", "sunglasses", "glasses", "ring",
        "bracelet", "necklace", "chain", "earring", "pendant", "brooch",
        "keychain", "umbrella", "pen", "notebook", "diary",
    ],
    "household": [
        "soap", "detergent", "shampoo", "toothpaste", "brush", "towel",
        "bedsheet", "pillow", "curtain", "bulb", "tube", "fan", "broom",
        "mop", "bucket", "dustbin", "tissue", "napkin", "cleaner",
        "freshener", "candle", "match", "lighter", "plate", "glass",
        "spoon", "fork", "knife", "pan", "pot", "container", "bottle",
    ],
}


# ── Tool Functions ─────────────────────────────────────────────────────────

async def parse_receipt_image(
    image_bytes: bytes,
    mime_type: str,
    tool_context: ToolContext,
) -> dict:
    """Parse a receipt image using Google Document AI Expense Parser.

    Call this tool when the user uploads a receipt photograph or scan.
    The tool extracts merchant name, date, total amount, and individual
    line items with prices.

    Args:
        image_bytes: Raw bytes of the receipt image.
        mime_type: MIME type of the image (e.g. 'image/jpeg', 'image/png').
        tool_context: ADK tool context for session state access.

    Returns:
        dict with keys: receipt_date, merchant_name, total_amount, currency,
        line_items (list), confidence, raw_text.
    """
    try:
        logger.info("Parsing receipt image (%d bytes, %s)", len(image_bytes), mime_type)
        result = ocr_service.parse_document(image_bytes, mime_type, doc_type="receipt")
        logger.info(
            "Receipt parsed: merchant=%s, items=%d",
            result.get("merchant_name"),
            len(result.get("line_items", [])),
        )
        return result
    except Exception as e:
        logger.error("Receipt parsing failed: %s", e, exc_info=True)
        return {"error": str(e), "status": "failed"}


async def parse_invoice_image(
    image_bytes: bytes,
    mime_type: str,
    tool_context: ToolContext,
) -> dict:
    """Parse an invoice image using Google Document AI Invoice Parser.

    Call this tool when the user uploads a formal invoice or bill (e.g.
    electronics purchase, warranty-covered product invoice). Extracts
    vendor info, invoice number, date, and line items.

    Args:
        image_bytes: Raw bytes of the invoice image.
        mime_type: MIME type of the image.
        tool_context: ADK tool context for session state access.

    Returns:
        dict with keys: receipt_date (invoice date), merchant_name (vendor),
        total_amount, currency, line_items, confidence, raw_text.
    """
    try:
        logger.info("Parsing invoice image (%d bytes, %s)", len(image_bytes), mime_type)
        result = ocr_service.parse_document(image_bytes, mime_type, doc_type="invoice")
        logger.info(
            "Invoice parsed: vendor=%s, items=%d",
            result.get("merchant_name"),
            len(result.get("line_items", [])),
        )
        return result
    except Exception as e:
        logger.error("Invoice parsing failed: %s", e, exc_info=True)
        return {"error": str(e), "status": "failed"}


async def structure_receipt_data(
    raw_entities: dict,
    tool_context: ToolContext,
) -> dict:
    """Normalise raw OCR entities into a standard receipt format.

    Call this tool after parse_receipt_image / parse_invoice_image to
    normalise dates to ISO-8601 (YYYY-MM-DD) and amounts to floats.

    Args:
        raw_entities: The raw dict returned by parse_receipt_image or
            parse_invoice_image.
        tool_context: ADK tool context.

    Returns:
        dict with normalised receipt_date (ISO str), total_amount (float),
        and line_items with numeric amount/quantity fields.
    """
    try:
        structured = dict(raw_entities)

        # ── Normalise date ──────────────────────────────────────────────
        raw_date = structured.get("receipt_date") or ""
        structured["receipt_date"] = _normalise_date(raw_date)

        # ── Normalise total amount ──────────────────────────────────────
        structured["total_amount"] = _parse_amount(structured.get("total_amount"))

        # ── Normalise line items ────────────────────────────────────────
        normalised_items = []
        for item in structured.get("line_items", []):
            normalised_items.append({
                "description": (item.get("description") or "").strip(),
                "amount": _parse_amount(item.get("amount")),
                "quantity": _parse_amount(item.get("quantity")) or 1.0,
                "unit_price": _parse_amount(item.get("unit_price")),
            })
        structured["line_items"] = normalised_items

        logger.info("Structured receipt: date=%s, total=%.2f, items=%d",
                     structured["receipt_date"],
                     structured["total_amount"] or 0,
                     len(normalised_items))
        return structured

    except Exception as e:
        logger.error("Structuring receipt data failed: %s", e, exc_info=True)
        return {"error": str(e), "status": "failed"}


async def categorize_items(
    items: list[dict],
    tool_context: ToolContext,
) -> list[dict]:
    """Add a 'category' field to each item based on keyword matching.

    Call this tool after structure_receipt_data to classify every line
    item into one of: food, clothing, electronics, accessories, household.
    If no match is found the item defaults to 'food'.

    Args:
        items: List of dicts, each with at least a 'description' key.
        tool_context: ADK tool context.

    Returns:
        The same list with an added 'category' field on every item.
    """
    try:
        categorised: list[dict] = []
        for item in items:
            desc = (item.get("description") or "").lower()
            category = _match_category(desc)
            enriched = {**item, "category": category}
            categorised.append(enriched)

        counts = {}
        for it in categorised:
            c = it["category"]
            counts[c] = counts.get(c, 0) + 1
        logger.info("Categorised %d items: %s", len(categorised), counts)

        return categorised

    except Exception as e:
        logger.error("Item categorisation failed: %s", e, exc_info=True)
        return items  # Return un-categorised as fallback


# ── Helpers ────────────────────────────────────────────────────────────────

def _normalise_date(raw: str) -> str:
    """Try multiple date formats and return ISO YYYY-MM-DD or empty string."""
    if not raw:
        return ""
    formats = [
        "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y",
        "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y",
        "%Y/%m/%d",
    ]
    cleaned = raw.strip()
    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Last resort — try ISO parse
    try:
        return datetime.fromisoformat(cleaned).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return cleaned


def _parse_amount(value) -> float | None:
    """Extract a float from a string that may contain currency symbols."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = re.sub(r"[^\d.]", "", str(value))
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def _match_category(description: str) -> str:
    """Return the best-matching category for a description."""
    for category, keywords in _CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in description:
                return category
    return "food"  # Default for grocery-focused app
