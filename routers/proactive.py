from fastapi import APIRouter, BackgroundTasks
from adk.proactive.expiry_scanner import run_daily_expiry_scan
from adk.proactive.budget_monitor import run_monthly_budget_scan

router = APIRouter(prefix="/api/proactive", tags=["Proactive"])

@router.post("/scan-expiry")
async def trigger_expiry_scan(background_tasks: BackgroundTasks, user_id: str = "default_user"):
    """
    Manually trigger the daily expiry scan. 
    In production, this is hit by Cloud Scheduler.
    """
    result = await run_daily_expiry_scan(user_id)
    return {"status": "ok", "result": result}

@router.post("/scan-budget")
async def trigger_budget_scan(background_tasks: BackgroundTasks, user_id: str = "default_user"):
    """
    Manually trigger the monthly budget scan.
    In production, this is hit by Cloud Scheduler.
    """
    result = await run_monthly_budget_scan(user_id)
    return {"status": "ok", "result": result}
