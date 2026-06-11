from fastapi import APIRouter, HTTPException, Query
from adk.demo.evidence_logger import get_session_trace, get_session_trace_from_db

router = APIRouter(prefix="/api/traces", tags=["Traces"])


@router.get("/{session_id}")
async def get_trace(
    session_id: str,
    source: str = Query("memory", description="'memory' = in-process ring buffer, 'db' = MongoDB")
):
    """
    Returns the event trace for an agent session.
    Use source=memory for live traces (faster, current run only).
    Use source=db for persistent traces (survives restarts, full history).
    """
    try:
        if source == "db":
            events = await get_session_trace_from_db(session_id)
        else:
            events = get_session_trace(session_id)

        return {
            "session_id": session_id,
            "source": source,
            "event_count": len(events),
            "events": events
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_recent_traces(limit: int = Query(20)):
    """Returns the most recent session IDs with traces in MongoDB."""
    try:
        from services.db_service import get_db_service
        db = get_db_service()
        pipeline = [
            {"$sort": {"ts": -1}},
            {"$group": {"_id": "$session_id", "latest_ts": {"$first": "$ts"}, "event_count": {"$sum": 1}}},
            {"$sort": {"latest_ts": -1}},
            {"$limit": limit}
        ]
        sessions = await db.aggregate("agent_traces", pipeline)
        return {"sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
