"""
evaluation/runner.py — Phase 3 · Day 3
========================================
Runs a single evaluation scenario against the live PantryMind server
by hitting the SSE streaming endpoint and collecting the full response + trace.
"""
import asyncio
import json
import logging
import uuid
from typing import AsyncGenerator

import httpx

from evaluation.scenarios import EvalScenario

logger = logging.getLogger("pantrymind.eval_runner")

SERVER_BASE = "http://localhost:8000"
SSE_ENDPOINT = f"{SERVER_BASE}/api/agent/chat"
TRACE_ENDPOINT = f"{SERVER_BASE}/api/traces"
APPROVALS_ENDPOINT = f"{SERVER_BASE}/api/approvals"


async def collect_sse_response(
    message: str,
    session_id: str,
    user_id: str = "eval_user",
    timeout: float = 60.0
) -> tuple[str, list[dict]]:
    """
    Sends message to SSE endpoint, collects full text response + stream events.
    Returns (full_response_text, stream_events).
    """
    payload = {"message": message, "session_id": session_id, "user_id": user_id}
    full_text = []
    stream_events = []

    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", SSE_ENDPOINT, json=payload) as resp:
            resp.raise_for_status()
            async for raw_line in resp.aiter_lines():
                if raw_line.startswith("data: "):
                    try:
                        event = json.loads(raw_line[6:])
                        stream_events.append(event)
                        if event.get("type") == "token":
                            full_text.append(event.get("data", ""))
                        elif event.get("type") == "done":
                            break
                    except json.JSONDecodeError:
                        pass

    return "".join(full_text), stream_events


async def fetch_trace(session_id: str) -> list[dict]:
    """Fetch trace events for this session from in-memory source."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{TRACE_ENDPOINT}/{session_id}?source=memory")
            return resp.json().get("events", [])
    except Exception as e:
        logger.warning(f"Could not fetch trace for {session_id}: {e}")
        return []


async def fetch_pending_actions(session_id: str) -> list[dict]:
    """Fetch any pending actions created during this session."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{APPROVALS_ENDPOINT}?status=pending")
            all_actions = resp.json().get("actions", [])
            return [a for a in all_actions if a.get("session_id") == session_id]
    except Exception as e:
        logger.warning(f"Could not fetch pending actions: {e}")
        return []


async def run_scenario(scenario: EvalScenario) -> dict:
    """
    Run a single evaluation scenario end-to-end.
    Returns a raw result dict (not yet scored).
    """
    session_id = f"eval_{scenario.id}_{uuid.uuid4().hex[:8]}"
    logger.info(f"▶  Running scenario {scenario.id}: {scenario.name}")
    logger.info(f"   Session: {session_id}")

    # Optional pre-scenario setup
    if scenario.setup:
        await scenario.setup()

    try:
        response_text, stream_events = await collect_sse_response(
            message=scenario.user_message,
            session_id=session_id
        )
        logger.info(f"   Response ({len(response_text)} chars): {response_text[:80]}...")
    except Exception as e:
        logger.error(f"   ❌ SSE call failed: {e}")
        return {
            "scenario_id": scenario.id,
            "session_id": session_id,
            "status": "error",
            "error": str(e),
            "response_text": "",
            "trace_events": [],
            "pending_actions": []
        }

    # Allow a brief window for async trace writes to flush
    await asyncio.sleep(1)

    trace_events = await fetch_trace(session_id)
    pending_actions = await fetch_pending_actions(session_id)

    logger.info(f"   Trace events: {len(trace_events)} | Pending actions: {len(pending_actions)}")

    return {
        "scenario_id": scenario.id,
        "scenario_name": scenario.name,
        "session_id": session_id,
        "status": "ok",
        "user_message": scenario.user_message,
        "response_text": response_text,
        "stream_event_count": len(stream_events),
        "trace_events": trace_events,
        "pending_actions": pending_actions
    }
