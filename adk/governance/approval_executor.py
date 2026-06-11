import logging
from adk.governance.pending_actions import get_action, update_action_status
from adk.governance.action_policy import evaluate_action_policy
from services.db_service import get_db_service

logger = logging.getLogger("pantrymind.governance")

async def execute_approved_action(action_id: str) -> dict:
    """
    Executes a pending action that has been approved.
    It reads the tool calls stored in the action and executes them safely
    using the db_service.
    """
    action = await get_action(action_id)
    if not action:
        raise ValueError(f"Action {action_id} not found")
        
    if action["status"] != "approved":
        raise ValueError(f"Action {action_id} cannot be executed in status '{action['status']}'. Must be 'approved'.")

    db_service = get_db_service()
    executed_count = 0
    results = []

    for call in action.get("tool_calls", []):
        tool_name = call.get("tool")
        collection = call.get("collection")
        arguments = call.get("arguments", {})
        
        # 1. Re-check policy to ensure no tampering
        policy_result = evaluate_action_policy(tool_name, collection, arguments)
        if policy_result["status"] == "blocked":
            logger.error(f"Execution blocked for tool {tool_name} on {collection}")
            raise PermissionError(f"Action blocked by policy: {policy_result['reason']}")

        # 2. Execute via db_service
        try:
            if tool_name == "insertOne":
                doc = arguments.get("document")
                if doc:
                    await db_service.insert_one(collection, doc)
                    executed_count += 1
            elif tool_name == "insertMany":
                docs = arguments.get("documents", [])
                if docs:
                    await db_service.insert_many(collection, docs)
                    executed_count += 1
            elif tool_name == "updateOne":
                query = arguments.get("query")
                update = arguments.get("update")
                if query and update:
                    await db_service.update_one(collection, query, update)
                    executed_count += 1
            elif tool_name == "updateMany":
                query = arguments.get("query")
                update = arguments.get("update")
                if query and update:
                    # Motor/PyMongo requires $set, ensure we format correctly if needed
                    await db_service.db[collection].update_many(query, update)
                    executed_count += 1
            else:
                logger.warning(f"Tool {tool_name} is not supported by Approval Executor.")
        except Exception as e:
            logger.error(f"Error executing {tool_name} on {collection}: {e}")
            raise

    # 3. Mark as executed
    await update_action_status(action_id, "executed")
    
    return {
        "action_id": action_id,
        "status": "executed",
        "executed_tool_calls": executed_count
    }
