import base64
from datetime import datetime
from data.expiry_rules import EXPIRY_DATASET
import google.generativeai as genai
import json
import os

RECEIPT_OCR_PROMPT = """
Analyze this receipt image and extract every line item.
Return ONLY valid JSON:
{
  "receipt_meta": {
    "store_name": "string or null",
    "receipt_date": "YYYY-MM-DD or null",
    "grand_total": number_or_null
  },
  "items": [
    {
      "item_name": "exact name from receipt",
      "normalized_name": "clean generic name",
      "category": "PRIMARY_CATEGORY",
      "sub_category": "sub_category_value",
      "dietary_flag": "VEG|NON_VEG|VEGAN|DAIRY|SEAFOOD|EGG|NA",
      "is_perishable": true_or_false,
      "is_packed_product": true_or_false,
      "quantity": number,
      "unit": "string",
      "total_price": number_or_null
    }
  ]
}
"""

def parse_receipt_image(image_bytes_b64: str) -> dict:
    """
    Calls Gemini 3.1 Flash Vision to extract items from receipt image.
    image_bytes_b64: base64-encoded JPEG bytes
    """
    model = genai.GenerativeModel(
        model_name=os.getenv("RECEIPT_MODEL", "gemini-3.1-flash"),
        generation_config=genai.GenerationConfig(
            temperature=0.1,
            response_mime_type="application/json"
        )
    )
    
    image_part = {
        "mime_type": "image/jpeg",
        "data": base64.b64decode(image_bytes_b64)
    }
    
    response = model.generate_content([RECEIPT_OCR_PROMPT, image_part])
    
    raw = response.text.strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:-1])
    
    return json.loads(raw)


def calculate_expiry_batch(items: list) -> list:
    """
    Adds expiry_date, safe_expiry_date, and status to each item.
    Wraps the existing expiry rules dataset logic.
    """
    now = datetime.utcnow()
    
    for item in items:
        cat     = item.get("category", "OTHER")
        sub_cat = item.get("sub_category", "default")
        
        cat_rules  = EXPIRY_DATASET.get(cat, EXPIRY_DATASET.get("OTHER", {}))
        item_rules = cat_rules.get(sub_cat) or cat_rules.get("default", {})
        
        shelf_life = item_rules.get("shelf_life_days")
        safety     = item_rules.get("safety_factor", 0.75)
        
        if shelf_life:
            from datetime import timedelta
            expiry_dt      = now + timedelta(days=shelf_life)
            safe_expiry_dt = now + timedelta(days=int(shelf_life * safety))
            
            days_left = (safe_expiry_dt - now).days
            
            item["purchase_date"]   = now.isoformat()
            item["expiry_date"]     = expiry_dt.isoformat()
            item["safe_expiry_date"]= safe_expiry_dt.isoformat()
            item["status"]          = (
                "Expired"       if days_left < 0 else
                "Critical"      if days_left <= 1 else
                "Expiring Soon" if days_left <= 3 else
                "Use This Week" if days_left <= 7 else
                "Fresh"
            )
            item["storage_note"]    = item_rules.get("storage_note", "")
        else:
            item["purchase_date"]    = now.isoformat()
            item["expiry_date"]      = None
            item["safe_expiry_date"] = None
            item["status"]           = "N/A"
        
        item["is_consumed"] = False
        item["source"]      = "receipt_scan"
    
    return items

from adk.memory.vector_memory import build_inventory_document_text, embed_text

def build_inventory_documents(items: list) -> list:
    """
    Shapes items for MongoDB insertMany.
    Phase 2: now generates embedding for each item before insert.
    """
    for item in items:
        doc_text          = build_inventory_document_text(item)
        item["embedding"] = embed_text(doc_text)
    return items

def build_ledger_entry(receipt_meta: dict) -> dict:
    return receipt_meta
