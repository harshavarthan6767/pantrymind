from __future__ import annotations

import re

from adk.tools.fast_db_tools import (
    get_finance_overview,
    get_inventory_overview,
    get_shopping_context,
)
from adk.tools.finance_tools import parse_date_range
from adk.tools.shopping_tools import (
    compute_ingredient_gaps,
    estimate_grocery_cost,
    format_shopping_list,
    prioritize_shopping_list,
)


def _mentions(query: str, keywords: tuple[str, ...]) -> bool:
    normalized = query.lower()
    return any(keyword in normalized for keyword in keywords)


def _is_simple_inventory_query(query: str) -> bool:
    return _mentions(query, (
        "inventory", "pantry", "fridge", "what do i have", "what's there",
        "what are the things", "stock", "items i have",
    ))


def _is_simple_finance_query(query: str) -> bool:
    return _mentions(query, (
        "spend", "spent", "expense", "expenses", "budget", "money",
        "how much", "financial", "ledger",
    ))


def _is_simple_shopping_query(query: str) -> bool:
    return _mentions(query, (
        "shopping list", "what should i buy", "what to buy", "groceries",
        "grocery", "restock", "running out", "need to buy",
    ))


def _is_simple_kitchen_query(query: str) -> bool:
    return _mentions(query, (
        "what can i cook", "what should i cook", "cook for", "make for",
        "prepare for", "dinner", "lunch", "breakfast", "recipe",
    ))


def _format_qty(item: dict) -> str:
    qty = item.get("quantity", 0)
    unit = item.get("unit") or ("item" if qty == 1 else "items")
    return f"{qty:g} {unit}" if isinstance(qty, (int, float)) else f"{qty} {unit}"


def _format_inventory(context: dict) -> str:
    if context.get("status") == "empty":
        return context.get("summary") or "Your pantry is empty. Scan a receipt to add inventory."

    lines = [f"You currently have {context.get('total_items', 0)} active inventory items."]

    expired = context.get("expired") or []
    if expired:
        lines.append("Expired: " + ", ".join(item["name"] for item in expired[:8]))

    expiring = context.get("expiring_soon") or []
    if expiring:
        lines.append("Expiring soon: " + ", ".join(item["name"] for item in expiring[:8]))

    categories = context.get("categories") or {}
    for category, items in sorted(categories.items()):
        if not items:
            continue
        names = [f"{item['name']} ({_format_qty(item)})" for item in items[:12]]
        lines.append(f"{category}: " + ", ".join(names))

    return "\n".join(lines)


def _format_finance(overview: dict) -> str:
    start = overview.get("start", "")[:10]
    end = overview.get("end", "")[:10]
    total = overview.get("total_expense", 0)
    lines = [f"From {start} to {end}, you spent Rs. {total:,.2f}."]

    categories = overview.get("by_category") or []
    if categories:
        top = ", ".join(
            f"{row['category']}: Rs. {row['total']:,.2f}"
            for row in categories[:5]
        )
        lines.append(f"Top categories: {top}.")
    else:
        lines.append("I did not find any expenses in that period.")

    recent = overview.get("recent_transactions") or []
    if recent:
        last = recent[0]
        desc = last.get("description") or last.get("category") or "latest transaction"
        lines.append(f"Most recent: {desc} for Rs. {last.get('amount', 0):,.2f}.")

    return " ".join(lines)


def _format_kitchen_from_inventory(context: dict) -> str:
    categories = context.get("categories") or {}
    usable = []

    for items in categories.values():
        for item in items:
            if item.get("expired"):
                continue
            usable.append(item)

    if not usable:
        return (
            "I can read your pantry, but everything currently looks expired or unavailable. "
            "Please scan a fresh receipt or add safe ingredients before meal planning."
        )

    names = [f"{item['name']} ({_format_qty(item)})" for item in usable[:8]]
    return (
        "For a quick meal, use these safe-looking pantry items: "
        + ", ".join(names)
        + ". For a full recipe with calories and macros, tell me the meal type and target calories."
    )


async def try_fast_path(user_id: str, message: str):
    """
    Return ADK-like events for common low-latency MongoDB read queries.
    Return None when the full ADK orchestrator should handle the request.
    """
    query = message.strip()
    if not query:
        return None

    lower = query.lower()

    if _is_simple_shopping_query(lower):
        context = await get_shopping_context(user_id)
        gaps = compute_ingredient_gaps(
            context["inventory"],
            context.get("dietary_preference", "NON_VEG"),
        )
        priced = estimate_grocery_cost(gaps)
        prioritized = prioritize_shopping_list(
            priced["items"],
            context.get("remaining_budget", 0),
        )
        text = format_shopping_list(prioritized)
        return [
            {"type": "agent", "data": "shopping_agent"},
            {"type": "tool_call", "data": "get_shopping_context", "agent": "shopping_agent"},
            {"type": "token", "data": text},
            {"type": "done", "data": ""},
        ]

    if _is_simple_finance_query(lower):
        range_name = "this month"
        if "last month" in lower:
            range_name = "last month"
        elif "last 30" in lower:
            range_name = "last 30 days"
        elif "last 7" in lower or "this week" in lower:
            range_name = "last 7 days"
        else:
            match = re.search(r"\b20\d{2}-\d{2}\b", lower)
            if match:
                range_name = match.group(0)

        date_range = parse_date_range(range_name)
        overview = await get_finance_overview(
            user_id=user_id,
            start_date=date_range["start"],
            end_date=date_range["end"],
        )
        return [
            {"type": "agent", "data": "finance_agent"},
            {"type": "tool_call", "data": "get_finance_overview", "agent": "finance_agent"},
            {"type": "token", "data": _format_finance(overview)},
            {"type": "done", "data": ""},
        ]

    if _is_simple_kitchen_query(lower):
        context = await get_inventory_overview(user_id)
        return [
            {"type": "agent", "data": "kitchen_chef_agent"},
            {"type": "tool_call", "data": "get_inventory_overview", "agent": "kitchen_chef_agent"},
            {"type": "token", "data": _format_kitchen_from_inventory(context)},
            {"type": "done", "data": ""},
        ]

    if _is_simple_inventory_query(lower):
        context = await get_inventory_overview(user_id)
        return [
            {"type": "agent", "data": "pantry_agent"},
            {"type": "tool_call", "data": "get_inventory_overview", "agent": "pantry_agent"},
            {"type": "token", "data": _format_inventory(context)},
            {"type": "done", "data": ""},
        ]

    return None
