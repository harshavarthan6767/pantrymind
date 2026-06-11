"""
Evidence Logger — Phase 3 · Day 2
Captures a structured, timestamped trace of every significant event
during an ADK agent run for hackathon judging evidence.

Each event is stored in MongoDB `agent_traces` collection and also
accumulated in-memory for the current session so the frontend can
render a live timeline.
"""
import datetime
import logging
from typing import Any, Literal

logger = logging.getLogger("pantrymind.evidence")

# ─── Trace event type definitions ─────────────────────────────────────────────
TraceEventType = Literal[
    "session_start",
    "agent_transfer",
    "tool_call",
    "tool_result",
    "approval_required",
    "approval_decision",
    "reflexion_check",
    "mcp_query",
    "mcp_write_blocked",
    "memory_recall",
    "memory_save",
    "final_response",
    "session_end",
    "error"
]

# ─── In-memory ring buffer (per session) ─────────────────────────────────────
_session_traces: dict[str, list[dict]] = {}


def _now_iso() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


def get_session_trace(session_id: str) -> list[dict]:
    """Return the in-memory trace list for a session."""
    return _session_traces.get(session_id, [])


def clear_session_trace(session_id: str) -> None:
    """Clear the in-memory trace for a session."""
    if session_id in _session_traces:
        del _session_traces[session_id]


# ─── Core logging function ─────────────────────────────────────────────────────
async def log_trace_event(
    session_id: str,
    event_type: TraceEventType,
    agent: str = "orchestrator",
    data: dict[str, Any] | None = None,
    persist: bool = True
) -> dict:
    """
    Log a single trace event.

    Args:
        session_id: The ADK session ID.
        event_type: One of the defined trace event types.
        agent: The agent or component that emitted this event.
        data: Arbitrary event payload (tool name, query, result preview, etc.)
        persist: Whether to also write to MongoDB (False for high-freq events).

    Returns:
        The trace event dict (with _id if persisted).
    """
    event = {
        "session_id": session_id,
        "ts": _now_iso(),
        "event_type": event_type,
        "agent": agent,
        "data": data or {}
    }

    # Accumulate in memory
    if session_id not in _session_traces:
        _session_traces[session_id] = []
    _session_traces[session_id].append(event)

    # Persist to MongoDB for durable evidence
    if persist:
        try:
            from services.db_service import get_db_service
            db = get_db_service()
            inserted_id = await db.insert_one("agent_traces", event.copy())
            event["_id"] = str(inserted_id)
        except Exception as e:
            logger.warning(f"Failed to persist trace event to MongoDB: {e}")

    logger.debug(f"TRACE [{event_type}] agent={agent} session={session_id}")
    return event


# ─── Convenience helpers ───────────────────────────────────────────────────────
async def trace_session_start(session_id: str, user_id: str, message: str) -> None:
    await log_trace_event(session_id, "session_start", "runner", {
        "user_id": user_id,
        "message_preview": message[:120]
    })


async def trace_agent_transfer(session_id: str, from_agent: str, to_agent: str) -> None:
    await log_trace_event(session_id, "agent_transfer", from_agent, {
        "to_agent": to_agent
    })


async def trace_tool_call(session_id: str, agent: str, tool_name: str, args_preview: str = "") -> None:
    await log_trace_event(session_id, "tool_call", agent, {
        "tool": tool_name,
        "args_preview": args_preview[:200]
    }, persist=False)  # high-freq — in-memory only


async def trace_mcp_query(session_id: str, agent: str, collection: str, operation: str) -> None:
    await log_trace_event(session_id, "mcp_query", agent, {
        "collection": collection,
        "operation": operation
    }, persist=False)


async def trace_mcp_write_blocked(session_id: str, agent: str, tool: str, collection: str, reason: str) -> None:
    await log_trace_event(session_id, "mcp_write_blocked", agent, {
        "tool": tool,
        "collection": collection,
        "reason": reason
    })


async def trace_approval_required(session_id: str, agent: str, action_id: str, summary: str, risk: str) -> None:
    await log_trace_event(session_id, "approval_required", agent, {
        "action_id": action_id,
        "summary": summary,
        "risk_level": risk
    })


async def trace_approval_decision(session_id: str, decision: str, action_id: str) -> None:
    await log_trace_event(session_id, "approval_decision", "user", {
        "decision": decision,
        "action_id": action_id
    })


async def trace_reflexion(session_id: str, agent: str, domain: str, changed: bool) -> None:
    await log_trace_event(session_id, "reflexion_check", agent, {
        "domain": domain,
        "draft_was_modified": changed
    })


async def trace_memory_recall(session_id: str, user_id: str, query_preview: str, hits: int) -> None:
    await log_trace_event(session_id, "memory_recall", "runner", {
        "user_id": user_id,
        "query_preview": query_preview[:80],
        "memory_hits": hits
    }, persist=False)


async def trace_final_response(session_id: str, agent: str, response_preview: str) -> None:
    await log_trace_event(session_id, "final_response", agent, {
        "response_preview": response_preview[:200]
    })


async def get_session_trace_from_db(session_id: str) -> list[dict]:
    """Load trace events from MongoDB for a given session."""
    try:
        from services.db_service import get_db_service
        db = get_db_service()
        return await db.find("agent_traces", {"session_id": session_id}, sort=[("ts", 1)], limit=200)
    except Exception as e:
        logger.error(f"Failed to load trace from DB: {e}")
        return []
