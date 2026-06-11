from datetime import datetime

# Minimum quantities before an item is considered "low" (in grams or ml)
STAPLE_THRESHOLDS = {
    "rice_pasta":         500,
    "flour":              500,
    "oil":                200,
    "legumes_pulses":     250,
    "salt":               100,
    "sugar":              200,
    "spices_seasoning":   50,
}

# Indian grocery price estimates ₹/base_unit (June 2026 approximate)
PRICE_DB = {
    "rice":              45,   # per kg
    "dal":              120,   # per kg
    "wheat flour":       45,   # per kg
    "atta":              45,   # per kg
    "oil":              150,   # per litre
    "onion":             30,   # per kg
    "tomato":            40,   # per kg
    "potato":            25,   # per kg
    "garlic":            80,   # per kg
    "ginger":           120,   # per kg
    "milk":              60,   # per litre
    "curd":              50,   # per 400g
    "eggs":               8,   # per egg
    "chicken":          300,   # per kg
    "paneer":           350,   # per kg
    "bread":             40,   # per loaf
    "salt":              20,   # per kg
    "sugar":             45,   # per kg
    "default":           80,   # fallback
}


def compute_ingredient_gaps(
    current_inventory: list,
    dietary_preference: str = "NON_VEG",
    meal_plan_requirements: list = None
) -> list:
    """
    Identifies what's missing or critically low.

    Returns list of dicts:
    {item, reason, current_qty, suggested_qty, unit, priority}
    Reasons: "depleted", "low", "expiring_replacement", "meal_plan_required"
    """
    # Build a lookup by sub_category
    inv_map = {}
    for item in current_inventory:
        key = item.get("sub_category", item.get("normalized_name", "")).lower()
        inv_map[key] = item

    gaps = []

    for sub_cat, min_qty in STAPLE_THRESHOLDS.items():
        matched = inv_map.get(sub_cat)
        if not matched:
            gaps.append({
                "item":          sub_cat.replace("_", " "),
                "reason":        "depleted",
                "current_qty":   0,
                "suggested_qty": min_qty,
                "unit":          "g",
                "priority":      1
            })
        elif matched.get("quantity", 0) < min_qty:
            gaps.append({
                "item":          matched.get("normalized_name", sub_cat),
                "reason":        "low",
                "current_qty":   matched.get("quantity", 0),
                "suggested_qty": min_qty - matched.get("quantity", 0),
                "unit":          matched.get("unit", "g"),
                "priority":      2
            })

    # Check for items with Critical/Expired status that need replacement
    for item in current_inventory:
        if item.get("status") in ("Critical", "Expired") and not item.get("is_consumed"):
            gaps.append({
                "item":          item.get("normalized_name", item.get("name")),
                "reason":        "expiring_replacement",
                "current_qty":   item.get("quantity", 0),
                "suggested_qty": 1,
                "unit":          item.get("unit", "unit"),
                "priority":      1
            })

    # Meal plan requirements
    if meal_plan_requirements:
        for req in meal_plan_requirements:
            req_name = req.get("name", "").lower()
            found = any(
                req_name in item.get("normalized_name", "").lower()
                for item in current_inventory
                if not item.get("is_consumed")
            )
            if not found:
                gaps.append({
                    "item":          req.get("name"),
                    "reason":        "meal_plan_required",
                    "current_qty":   0,
                    "suggested_qty": req.get("quantity", 1),
                    "unit":          req.get("unit", "unit"),
                    "priority":      1
                })

    return sorted(gaps, key=lambda x: x.get("priority", 3))


def estimate_grocery_cost(items: list) -> dict:
    """Adds estimated ₹ cost to each shopping list item."""
    total       = 0
    priced      = []

    for item in items:
        name           = item.get("item", "").lower()
        price_per_unit = PRICE_DB["default"]
        for key, price in PRICE_DB.items():
            if key in name or name in key:
                price_per_unit = price
                break

        qty  = item.get("suggested_qty", 1)
        unit = item.get("unit", "unit")

        # Convert grams to kg for kg-priced items.
        if unit == "g":
            cost = price_per_unit * (qty / 1000)
        else:
            cost = price_per_unit * qty

        cost = round(cost, 2)
        total += cost
        priced.append({**item, "estimated_cost": cost})

    return {
        "items":           priced,
        "total_estimated": round(total, 2),
        "currency":        "INR"
    }


def prioritize_shopping_list(items: list, remaining_budget: float) -> dict:
    """Splits items into priority tiers, drops P2/P3 if budget is tight."""
    p1 = [i for i in items if i.get("priority") == 1]
    p2 = [i for i in items if i.get("priority") == 2]
    p3 = [i for i in items if i.get("priority") == 3]

    p1_cost   = sum(i.get("estimated_cost", 0) for i in p1)
    all_cost  = sum(i.get("estimated_cost", 0) for i in items)
    can_all   = all_cost <= remaining_budget

    return {
        "priority_1":    p1,
        "priority_2":    p2 if can_all else [],
        "priority_3":    p3 if can_all else [],
        "p1_total":      round(p1_cost, 2),
        "total_all":     round(all_cost, 2),
        "within_budget": can_all,
        "budget_note":   None if can_all else (
            f"Full list (₹{all_cost:.0f}) exceeds remaining food budget (₹{remaining_budget:.0f}). "
            f"Showing Priority 1 only (₹{p1_cost:.0f})."
        )
    }


def format_shopping_list(prioritized: dict) -> str:
    """Formats the shopping list as a printable string."""
    date_str = datetime.now().strftime("%d %b %Y")
    lines    = [f"🛒 SHOPPING LIST — {date_str}"]

    if prioritized.get("budget_note"):
        lines.append(f"\n⚠️  {prioritized['budget_note']}")

    for tier_key, label in [
        ("priority_1", "PRIORITY 1 — Must Buy"),
        ("priority_2", "PRIORITY 2 — Restock Soon"),
        ("priority_3", "PRIORITY 3 — Nice to Have"),
    ]:
        items = prioritized.get(tier_key, [])
        if not items:
            continue
        lines.append(f"\n{label}:")
        for item in items:
            qty    = item.get("suggested_qty", "")
            unit   = item.get("unit") or ""
            qty_text = f"{qty} {unit}".strip()
            cost   = item.get("estimated_cost", 0)
            reason = item.get("reason", "")
            reason_tag = f" · {reason.replace('_', ' ')}" if reason else ""
            lines.append(f"  [ ] {item['item']} — ₹{cost:.0f} (qty: {qty_text}{reason_tag})")

    p1  = prioritized.get("p1_total", 0)
    all = prioritized.get("total_all", 0)
    lines.append(f"\nEstimated total (P1): ₹{p1:.0f}")
    if prioritized.get("priority_2"):
        lines.append(f"Estimated total (P1+P2): ₹{all:.0f}")

    return "\n".join(lines)
