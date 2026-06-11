from datetime import datetime, timedelta
from typing import Optional

from data.expiry_rules import EXPIRY_DATASET


def calculate_expiry_dates(
    category: str,
    sub_category: str,
    purchase_date: datetime,
    is_packed_product: bool
) -> dict:
    """
    Returns both expiry_date (max) and safe_expiry_date (conservative)
    
    Logic:
    - For fresh items (PRODUCE, MEAT_SEAFOOD, DAIRY): use 50% safety factor
    - For packed/frozen items: use 75% safety factor  
    - For non-food: return None for both dates
    """
    
    # Get category rules
    cat_rules = EXPIRY_DATASET.get(category, EXPIRY_DATASET["OTHER"])
    
    # Get sub-category rules (fallback to default)
    item_rules = cat_rules.get(sub_category) or cat_rules.get("default")
    
    if not item_rules or item_rules.get("shelf_life_days") is None:
        # Non-food item or no expiry applicable
        return {
            "expiry_date": None,
            "safe_expiry_date": None,
            "shelf_life_days": None,
            "safe_days": None,
            "storage_note": item_rules.get("storage_note", "No expiry applicable"),
            "track_as_warranty": cat_rules.get("_meta", {}).get("track_as_warranty", False)
        }
    
    shelf_life = item_rules["shelf_life_days"]
    safety_factor = item_rules["safety_factor"]
    safe_days = item_rules.get("safe_days") or int(shelf_life * safety_factor)
    
    # Override: packed products always get at least 75% safety factor
    if is_packed_product and safety_factor < 0.75:
        safety_factor = 0.75
        safe_days = int(shelf_life * 0.75)
    
    expiry_date = purchase_date + timedelta(days=shelf_life)
    safe_expiry_date = purchase_date + timedelta(days=safe_days)
    
    return {
        "expiry_date": expiry_date,
        "safe_expiry_date": safe_expiry_date,
        "shelf_life_days": shelf_life,
        "safe_days": safe_days,
        "safety_factor_applied": safety_factor,
        "storage_note": item_rules.get("storage_note", ""),
        "track_as_warranty": False
    }


def get_item_status(safe_expiry_date: Optional[datetime]) -> str:
    """
    Calculate display status based on safe expiry (not max expiry)
    """
    if safe_expiry_date is None:
        return "N/A"
    
    now = datetime.utcnow()
    # If safe_expiry_date is naive, the above will work. If aware, it will raise an error.
    # We will assume safe_expiry_date is naive UTC, just like datetime.utcnow().
    days_remaining = (safe_expiry_date - now).days
    
    if days_remaining < 0:
        return "Expired"
    elif days_remaining <= 1:
        return "Critical"      # Red — use today!
    elif days_remaining <= 3:
        return "Expiring Soon"  # Orange
    elif days_remaining <= 7:
        return "Use This Week"  # Yellow
    else:
        return "Fresh"          # Green
