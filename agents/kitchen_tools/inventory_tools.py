from datetime import datetime, timedelta
from bson import ObjectId
from agents.kitchen_tools.macro_roles import MACRO_ROLE_TO_CATEGORY_QUERY, DIETARY_FILTERS
from services.meal_optimizer import run_meal_optimizer
from data.nutrition_db import NUTRITION_DB

async def get_pantry_by_macro_role(
    db,
    user_id: str,
    role: str,                        # "protein", "carbohydrate", "vegetable", "fat", "flavoring", "grain", "dairy"
    dietary_preference: str = None,   # "VEG", "VEGAN", "NON_VEG", "KETO"
    exclude_expired: bool = True,
    prioritize_expiring: bool = True
) -> dict:
    """
    Category-aware pantry query — the Kitchen Agent's primary inventory tool.

    Returns items grouped by sub_category, sorted by expiry urgency.
    The agent receives a clean, cooking-oriented view of the pantry
    instead of a flat list of raw item names.
    """

    role_config = MACRO_ROLE_TO_CATEGORY_QUERY.get(role)
    if not role_config:
        return {"error": f"Unknown macro role: {role}. Choose from: protein, carbohydrate, vegetable, fat, flavoring, grain, dairy"}

    # Build the base match filter.
    # IMPORTANT: Use $ne: true instead of False, because many items don't have is_consumed field at all.
    # In MongoDB, {field: false} does NOT match documents where the field is missing.
    match_filter = {
        "is_consumed": {"$ne": True},
        "user_id": user_id,
        **role_config["mongo_filter"]
    }
    
    # Add dietary restriction filter
    if dietary_preference and dietary_preference in DIETARY_FILTERS:
        match_filter.update(DIETARY_FILTERS[dietary_preference])

    # Exclude expired items (based on safe_expiry_date, not just status field)
    # IMPORTANT: Many items don't have safe_expiry_date at all.
    # Use $or to include items with no expiry OR items whose expiry is in the future.
    # Also check the "status" field as a fallback ("expired" items should be excluded).
    if exclude_expired:
        match_filter["$and"] = match_filter.get("$and", []) + [
            {"status": {"$nin": ["expired", "Expired"]}},
            {"$or": [
                {"safe_expiry_date": {"$exists": False}},
                {"safe_expiry_date": None},
                {"safe_expiry_date": ""},
                {"safe_expiry_date": {"$gt": datetime.utcnow().isoformat()}},
            ]}
        ]

    # Sort by expiry urgency (most urgent first)
    sort_field = "safe_expiry_date" if prioritize_expiring else "item_name"

    # Aggregation pipeline
    # Since safe_expiry_date is a string, $dateDiff might fail if MongoDB can't parse it automatically.
    # To be safe, we will fetch and do the date math in Python.
    pipeline = [
        {"$match": match_filter},
        {"$sort": {sort_field: 1}},
        {
            "$group": {
                "_id": "$sub_category",
                "items": {
                    "$push": {
                        "item_id":      {"$toString": "$_id"},
                        "name":         "$normalized_name",
                        "display_name": "$item_name",
                        "quantity":     "$quantity",
                        "unit":         "$unit",
                        "dietary_flag": "$dietary_flag",
                        "status":       "$status",
                        "safe_expiry_date": "$safe_expiry_date"
                    }
                },
                "total_items": {"$sum": 1},
                "expiring_soon_count": {
                    "$sum": {
                        "$cond": [{"$eq": ["$status", "Expiring Soon"]}, 1, 0]
                    }
                }
            }
        },
        {
            "$project": {
                "sub_category": "$_id",
                "_id": 0,
                "items": 1,
                "total_items": 1,
                "expiring_soon_count": 1
            }
        }
    ]

    result = await db.aggregate("inventory", pipeline)

    # Flatten into agent-friendly format and compute date differences locally
    now = datetime.utcnow()
    all_items = []
    expiring_items = []
    
    for group in result:
        for item in group["items"]:
            item["sub_category"] = group["sub_category"]
            
            # Date diff calculation
            safe_exp_str = item.get("safe_expiry_date")
            is_expiring = False
            if safe_exp_str:
                try:
                    exp_date = datetime.fromisoformat(safe_exp_str)
                    days_left = (exp_date - now).days
                    item["days_left"] = days_left
                    if days_left <= 3:
                        is_expiring = True
                except:
                    item["days_left"] = 999
            else:
                item["days_left"] = 999
                
            item["is_expiring"] = is_expiring
            
            all_items.append(item)
            if is_expiring:
                expiring_items.append(item)

    return {
        "role": role,
        "description": role_config["description"],
        "dietary_filter_applied": dietary_preference,
        "total_items": len(all_items),
        "expiring_items": expiring_items,
        "by_sub_category": result,
        "flat_list": all_items    # What the LP optimizer receives
    }


async def search_inventory(
    db,
    user_id: str,
    category: str = None,          # e.g. "MEAT_SEAFOOD", "PRODUCE"
    sub_category: str = None,      # e.g. "poultry", "leafy_greens"
    dietary_flag: str = None,      # e.g. "VEG", "NON_VEG", "SEAFOOD"
    name_contains: str = None,     # partial name match e.g. "chicken"
    exclude_expired: bool = True,
    limit: int = 50
) -> dict:
    """
    Generalized inventory search — the Kitchen Agent's flexible query tool.

    Accepts any combination of filters: category, sub_category, dietary_flag,
    and name substring match. If no filters are provided, returns the full
    available inventory (up to limit).
    """
    match_filter = {
        "is_consumed": {"$ne": True},
        "user_id": user_id
    }

    if category:
        match_filter["category"] = category
    if sub_category:
        match_filter["sub_category"] = sub_category
    if dietary_flag:
        if dietary_flag in DIETARY_FILTERS:
            match_filter.update(DIETARY_FILTERS[dietary_flag])
        else:
            match_filter["dietary_flag"] = dietary_flag
    if name_contains:
        match_filter["$or"] = match_filter.get("$or", []) + [
            {"name": {"$regex": name_contains, "$options": "i"}},
            {"normalized_name": {"$regex": name_contains, "$options": "i"}},
        ]

    if exclude_expired:
        now_iso = datetime.utcnow().isoformat()
        match_filter["$and"] = match_filter.get("$and", []) + [
            {"status": {"$nin": ["expired", "Expired"]}},
            {"$or": [
                {"safe_expiry_date": {"$exists": False}},
                {"safe_expiry_date": None},
                {"safe_expiry_date": ""},
                {"safe_expiry_date": {"$gt": now_iso}},
            ]}
        ]

    items = await db.find("inventory", match_filter, limit=limit, sort=[("safe_expiry_date", 1)])

    now = datetime.utcnow()
    results = []
    for item in items:
        days_left = 999
        safe_exp = item.get("safe_expiry_date")
        if safe_exp:
            try:
                days_left = (datetime.fromisoformat(safe_exp) - now).days
            except:
                pass

        results.append({
            "item_id": str(item["_id"]),
            "name": item.get("name", ""),
            "normalized_name": item.get("normalized_name", ""),
            "category": item.get("category", ""),
            "sub_category": item.get("sub_category", ""),
            "dietary_flag": item.get("dietary_flag", ""),
            "quantity": item.get("quantity", 0),
            "unit": item.get("unit", ""),
            "status": item.get("status", ""),
            "days_left": days_left,
        })

    return {
        "filters_applied": {
            "category": category,
            "sub_category": sub_category,
            "dietary_flag": dietary_flag,
            "name_contains": name_contains,
        },
        "total_items": len(results),
        "items": results,
    }

async def get_expiring_items(db, user_id: str, within_days: int = 3) -> dict:
    """
    Returns all food items expiring within N days across ALL categories.
    """
    cutoff = (datetime.utcnow() + timedelta(days=within_days)).isoformat()
    now_str = datetime.utcnow().isoformat()
    
    items = await db.find(
        "inventory",
        {
            "user_id": user_id,
            "is_consumed": {"$ne": True},
            "$or": [
                {"safe_expiry_date": {"$lte": cutoff, "$gte": now_str}},
                # Also include items with status "expiring" but no safe_expiry_date
                {"status": {"$in": ["expiring", "Expiring", "Expiring Soon"]}},
            ],
            "dietary_flag": {"$ne": "NA"}    # Exclude non-food
        },
        sort=[("safe_expiry_date", 1)],
        limit=30
    )

    now = datetime.utcnow()
    res_items = []
    for i in items:
        safe_exp = i.get("safe_expiry_date")
        days_left = 0
        if safe_exp:
            try:
                days_left = (datetime.fromisoformat(safe_exp) - now).days
            except:
                pass
                
        res_items.append({
            "name": i.get("normalized_name") or i.get("name"),
            "category": i.get("category"),
            "sub_category": i.get("sub_category"),
            "dietary_flag": i.get("dietary_flag"),
            "days_left": days_left,
            "quantity": i.get("quantity"),
            "unit": i.get("unit"),
            "item_id": str(i["_id"])
        })

    return {
        "expiring_within_days": within_days,
        "count": len(res_items),
        "items": res_items
    }


async def get_user_kitchen_profile(db, user_id: str) -> dict:
    """
    Retrieves user's nutrition goals, dietary preferences, and
    recent meal history for context-aware planning.
    """
    profile = await db.find_one("user_kitchen_profiles", {"user_id": user_id})
    if not profile:
        return {
            "calorie_target": 2000,
            "dietary_preference": "NON_VEG",
            "macro_split": {"protein_pct": 30, "carb_pct": 40, "fat_pct": 30},
            "allergies": [],
            "meal_history_last_7_days": [],
            "is_default": True
        }

    recent_meals = await db.find(
        "meal_plans",
        {
            "user_id": user_id,
            "created_at": {"$gte": (datetime.utcnow() - timedelta(days=7)).isoformat()}
        },
        sort=[("created_at", -1)],
        limit=7
    )

    return {
        "calorie_target": profile.get("calorie_target", 2000),
        "dietary_preference": profile.get("dietary_preference", "NON_VEG"),
        "macro_split": profile.get("macro_split", {"protein_pct": 30, "carb_pct": 40, "fat_pct": 30}),
        "allergies": profile.get("allergies", []),
        "dislikes": profile.get("dislikes", []),
        "meal_history_last_7_days": [m.get("meal_names", []) for m in recent_meals],
        "is_default": False
    }


async def optimize_meal_with_lp(
    available_ingredients: list,
    nutrition_db: dict,
    targets: dict,
    meal_type: str = "dinner"
) -> dict:
    """
    Calls the PuLP optimizer service.
    Returns exact gram amounts for each ingredient that hit macro targets.
    """
    result = run_meal_optimizer(available_ingredients, nutrition_db, targets, meal_type)
    return result


async def log_meal_consumed(
    db,
    user_id: str,
    meal_plan_id: str,
    items_consumed: list
) -> dict:
    """
    Marks inventory items as consumed and logs nutrition for the day.
    """
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_str = today.isoformat()

    total_nutrition = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}

    for item in items_consumed:
        item_doc = await db.find_one("inventory", {"_id": ObjectId(item["item_id"])})
        if not item_doc:
            continue

        grams_used = float(item["grams_used"])
        current_qty = float(item_doc.get("quantity", 0))

        if current_qty <= 1:
            await db.update_one(
                "inventory",
                {"_id": ObjectId(item["item_id"])},
                {"$set": {"is_consumed": True, "consumed_at": datetime.utcnow().isoformat()}}
            )
        else:
            await db.update_one(
                "inventory",
                {"_id": ObjectId(item["item_id"])},
                {"$set": {"quantity": max(0, current_qty - 1)}}
            )

        norm_name = item_doc.get("normalized_name", "")
        if norm_name in NUTRITION_DB:
            macros = NUTRITION_DB[norm_name]
            factor = grams_used / 100
            total_nutrition["calories"] += macros["calories"] * factor
            total_nutrition["protein"]  += macros["protein"]  * factor
            total_nutrition["carbs"]    += macros["carbs"]    * factor
            total_nutrition["fat"]      += macros["fat"]      * factor

    await db.update_one(
        "nutrition_logs",
        {"user_id": user_id, "date": today_str},
        {
            "$inc": {
                "calories": round(total_nutrition["calories"], 1),
                "protein":  round(total_nutrition["protein"],  1),
                "carbs":    round(total_nutrition["carbs"],    1),
                "fat":      round(total_nutrition["fat"],      1),
            },
            "$push": {
                "meals_logged": {
                    "meal_plan_id": meal_plan_id,
                    "logged_at": datetime.utcnow().isoformat(),
                    "nutrition": {k: round(v, 1) for k, v in total_nutrition.items()}
                }
            },
            "$setOnInsert": {"date": today_str, "user_id": user_id}
        },
        upsert=True
    )

    return {
        "logged": True,
        "items_consumed": len(items_consumed),
        "nutrition_added_today": {k: round(v, 1) for k, v in total_nutrition.items()}
    }


async def add_to_shopping_list(
    db,
    user_id: str,
    missing_ingredients: list
) -> dict:
    """
    When the AI Chef needs an ingredient that's not in the pantry.
    """
    inserts = []
    for ingredient in missing_ingredients:
        inserts.append({
            "user_id": user_id,
            "item_name": ingredient["name"],
            "quantity": ingredient.get("quantity"),
            "reason": ingredient.get("reason"),
            "source": "ai_chef",
            "is_purchased": False,
            "added_at": datetime.utcnow().isoformat()
        })

    if inserts:
        for doc in inserts:
            await db.insert_one("shopping_list", doc)

    return {
        "added_to_shopping_list": len(inserts),
        "items": [i["item_name"] for i in inserts]
    }
