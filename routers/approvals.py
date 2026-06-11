from fastapi import APIRouter, HTTPException, Query
from adk.governance.pending_actions import get_pending_actions, get_action, update_action_status
from adk.governance.approval_executor import execute_approved_action

router = APIRouter(prefix="/api/approvals", tags=["Approvals"])

@router.get("")
async def list_approvals(
    user_id: str = Query("default_user"),
    status: str = Query("pending")
):
    """List pending actions for a user."""
    try:
        actions = await get_pending_actions(user_id=user_id, status=status)
        return {"actions": actions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{action_id}")
async def get_approval(action_id: str):
    """Get a specific action by ID."""
    action = await get_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    return action

@router.post("/{action_id}/approve")
async def approve_action(action_id: str):
    """Approve a pending action."""
    action = await get_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Action is already {action['status']}")
        
    success = await update_action_status(action_id, "approved")
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update action status")
    return {"ok": True, "action_id": action_id, "status": "approved"}

@router.post("/{action_id}/reject")
async def reject_action(action_id: str):
    """Reject a pending action."""
    action = await get_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Action is already {action['status']}")
        
    success = await update_action_status(action_id, "rejected")
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update action status")
    return {"ok": True, "action_id": action_id, "status": "rejected"}

@router.post("/{action_id}/execute")
async def execute_action(action_id: str):
    """Execute an approved action."""
    try:
        result = await execute_approved_action(action_id)
        # TODO: Add trace logging logic here when trace_id is generated
        result["trace_id"] = "pending_trace_id_implementation"
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
