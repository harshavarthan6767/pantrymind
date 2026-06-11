import re
import os

MAIN_PY = r"D:\pantrymind-desktop\main.py"

with open(MAIN_PY, "r", encoding="utf-8") as f:
    content = f.read()

# 1. get_inventory
content = content.replace(
    'async def get_inventory(category: str | None = None):',
    'async def get_inventory(category: str | None = None, user_id: str = Depends(get_current_user)):'
)
content = content.replace(
    'query = {"quantity": {"$gt": 0}}',
    'query = {"quantity": {"$gt": 0}, "user_id": user_id}'
)

# 2. delete_inventory_item
content = content.replace(
    'async def delete_inventory_item(item_id: str):',
    'async def delete_inventory_item(item_id: str, user_id: str = Depends(get_current_user)):'
)
content = content.replace(
    'deleted = await db_service.delete_one("inventory", {"_id": oid})',
    'deleted = await db_service.delete_one("inventory", {"_id": oid, "user_id": user_id})'
)

# 3. bulk_delete_inventory_items
content = content.replace(
    'async def bulk_delete_inventory_items(req: BulkDeleteRequest):',
    'async def bulk_delete_inventory_items(req: BulkDeleteRequest, user_id: str = Depends(get_current_user)):'
)
content = content.replace(
    'deleted = await db_service.delete_many("inventory", {"_id": {"$in": oids}})',
    'deleted = await db_service.delete_many("inventory", {"_id": {"$in": oids}, "user_id": user_id})'
)

# 4. consume_item
content = content.replace(
    'async def consume_item(',
    'async def consume_item(\n    user_id: str = Depends(get_current_user),'
)
content = content.replace(
    '{"name": {"$regex": regex_pattern, "$options": "i"}}',
    '{"name": {"$regex": regex_pattern, "$options": "i"}, "user_id": user_id}'
)
content = content.replace(
    '{"_id": ObjectId(item["_id"])}',
    '{"_id": ObjectId(item["_id"]), "user_id": user_id}'
)
content = content.replace(
    '"item_name": item.get("name", item_name),',
    '"item_name": item.get("name", item_name),\n        "user_id": user_id,'
)

# 5. get_dashboard_stats
content = content.replace(
    'async def get_dashboard_stats():',
    'async def get_dashboard_stats(user_id: str = Depends(get_current_user)):'
)
content = content.replace(
    '{"$match": {"date": {"$gte": month_start.isoformat()}}}',
    '{"$match": {"date": {"$gte": month_start.isoformat()}, "user_id": user_id}}'
)
content = content.replace(
    'total_items_task = db_service.count_documents("inventory", {})',
    'total_items_task = db_service.count_documents("inventory", {"user_id": user_id})'
)
content = content.replace(
    'expiring_items_task = db_service.find("inventory", {"status": "expiring"})',
    'expiring_items_task = db_service.find("inventory", {"status": "expiring", "user_id": user_id})'
)
content = content.replace(
    'recent_receipts_task = db_service.find("receipts", {}, limit=3, sort=[("date", -1)])',
    'recent_receipts_task = db_service.find("receipts", {"user_id": user_id}, limit=3, sort=[("date", -1)])'
)

# 6. get_receipts
content = content.replace(
    'async def get_receipts():',
    'async def get_receipts(user_id: str = Depends(get_current_user)):'
)
content = content.replace(
    'await db_service.find(\n        "receipts", {}',
    'await db_service.find(\n        "receipts", {"user_id": user_id}'
)

# 7. finance_chat
content = content.replace(
    'async def finance_chat(body: ChatRequest):',
    'async def finance_chat(body: ChatRequest, user_id: str = Depends(get_current_user)):'
)
content = content.replace(
    'finance_chat_service.process_message(\n            session_id=session_id,\n            user_message=body.message,\n        )',
    'finance_chat_service.process_message(\n            session_id=session_id,\n            user_message=body.message,\n            user_id=user_id\n        )'
)

# 8. get_finance_chat_history
content = content.replace(
    'async def get_finance_chat_history(session_id: str):',
    'async def get_finance_chat_history(session_id: str, user_id: str = Depends(get_current_user)):'
)
content = content.replace(
    'await finance_chat_service.load_history(session_id, limit=50)',
    'await finance_chat_service.load_history(session_id, limit=50, user_id=user_id)'
)

# 9. get_finance_transactions
content = content.replace(
    'async def get_finance_transactions():',
    'async def get_finance_transactions(user_id: str = Depends(get_current_user)):'
)
content = content.replace(
    'await db_service.find(\n        "financial_ledger", {}',
    'await db_service.find(\n        "financial_ledger", {"user_id": user_id}'
)

# 10. create_finance_transaction
content = content.replace(
    'async def create_finance_transaction(req: TransactionRequest):',
    'async def create_finance_transaction(req: TransactionRequest, user_id: str = Depends(get_current_user)):'
)
content = content.replace(
    '"date": datetime.utcnow().isoformat()',
    '"user_id": user_id,\n        "date": datetime.utcnow().isoformat()'
)

# 11. get_financial_summary
content = content.replace(
    'async def get_financial_summary():',
    'async def get_financial_summary(user_id: str = Depends(get_current_user)):'
)
content = content.replace(
    '{"$match": {"type": "expense"}},',
    '{"$match": {"type": "expense", "user_id": user_id}},'
)

# 12. get_carbon_footprint
content = content.replace(
    'async def get_carbon_footprint():',
    'async def get_carbon_footprint(user_id: str = Depends(get_current_user)):'
)
content = content.replace(
    'await db_service.find("carbon_log", {}',
    'await db_service.find("carbon_log", {"user_id": user_id}'
)

# 13. get_nutrition_report
content = content.replace(
    'async def get_nutrition_report():',
    'async def get_nutrition_report(user_id: str = Depends(get_current_user)):'
)
content = content.replace(
    'await db_service.find("nutrition_log", {}',
    'await db_service.find("nutrition_log", {"user_id": user_id}'
)

# 14. get_restock_alerts
content = content.replace(
    'async def get_restock_alerts():',
    'async def get_restock_alerts(user_id: str = Depends(get_current_user)):'
)
content = content.replace(
    'await db_service.find("inventory", {"quantity": {"$lte": 1}})',
    'await db_service.find("inventory", {"quantity": {"$lte": 1}, "user_id": user_id})'
)

# 15. KitchenChatRequest fixes
content = content.replace(
    'user_id: str = "default_user"  # In a real app, this comes from auth token',
    ''
)
content = content.replace(
    'async def handle_kitchen_chat(request: KitchenChatRequest):',
    'async def handle_kitchen_chat(request: KitchenChatRequest, user_id: str = Depends(get_current_user)):'
)
content = content.replace(
    'user_id=request.user_id',
    'user_id=user_id'
)

with open(MAIN_PY, "w", encoding="utf-8") as f:
    f.write(content)

print("Replacement successful")
