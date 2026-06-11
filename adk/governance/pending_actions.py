import datetime
from bson import ObjectId
from services.db_service import get_db_service

async def create_pending_action(
    user_id: str,
    session_id: str,
    agent_name: str,
    action_type: str,
    risk_level: str,
    summary: str,
    tool_calls: list[dict],
    diff_preview: dict,
    confidence: float = 1.0,
    expires_in_days: int = 7
) -> str:
    """
    Creates a pending action in the database awaiting user approval.
    """
    db_service = get_db_service()
    now = datetime.datetime.utcnow()
    expires_at = now + datetime.timedelta(days=expires_in_days)
    
    document = {
        "user_id": user_id,
        "session_id": session_id,
        "agent_name": agent_name,
        "action_type": action_type,
        "risk_level": risk_level,
        "status": "pending",
        "summary": summary,
        "tool_calls": tool_calls,
        "diff_preview": diff_preview,
        "confidence": confidence,
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "approved_at": None,
        "rejected_at": None,
        "executed_at": None
    }
    
    return await db_service.insert_one("pending_actions", document)


async def get_pending_actions(user_id: str = "default_user", status: str = "pending") -> list[dict]:
    """
    Fetches all pending actions for a user.
    """
    db_service = get_db_service()
    query = {"user_id": user_id}
    if status:
        query["status"] = status
        
    actions = await db_service.find("pending_actions", query, sort=[("created_at", -1)])
    return actions


async def get_action(action_id: str) -> dict | None:
    """
    Gets a specific action by ID.
    """
    db_service = get_db_service()
    return await db_service.find_one("pending_actions", {"_id": ObjectId(action_id)})


async def update_action_status(action_id: str, status: str) -> bool:
    """
    Updates the status of a pending action (e.g., approved, rejected, executed).
    """
    db_service = get_db_service()
    now = datetime.datetime.utcnow().isoformat()
    
    update_data = {"status": status}
    if status == "approved":
        update_data["approved_at"] = now
    elif status == "rejected":
        update_data["rejected_at"] = now
    elif status == "executed":
        update_data["executed_at"] = now
        
    modified = await db_service.update_one(
        "pending_actions", 
        {"_id": ObjectId(action_id)}, 
        {"$set": update_data}
    )
    return modified > 0
