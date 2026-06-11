async def simulate_platform_order(
    user_id: str,
    items: list[dict],
) -> dict:
    """
    Simulate an external grocery-platform order, add the bought items to
    inventory, and record the exact spend in the finance ledger.
    """
    from agents.ordering_tools import simulate_platform_order as _simulate_order
    from services.db_service import get_db

    db = await get_db()
    return await _simulate_order(db, user_id, items)
