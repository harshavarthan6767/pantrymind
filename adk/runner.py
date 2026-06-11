import os
import asyncio
import logging
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService, VertexAiSessionService
from google.adk.events import Event
from google.genai.types import Content, Part
from adk.orchestrator import create_pantry_mind_orchestrator
from adk.fast_path import try_fast_path
from adk.memory.episodic_memory import retrieve_relevant_memories, summarize_and_store_session
from adk.demo.evidence_logger import (
    trace_session_start,
    trace_agent_transfer,
    trace_tool_call,
    trace_final_response,
    trace_memory_recall,
    get_session_trace
)

APP_NAME = "pantrymind"
logger = logging.getLogger("pantrymind.adk.runner")

# Session service — InMemory for dev, Vertex for production
def get_session_service():
    env = os.getenv("APP_ENV", "development")
    if env == "production":
        # VertexAiSessionService persists sessions to Google Cloud
        # Sessions survive server restarts and scale across instances
        return VertexAiSessionService(
            project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        )
    else:
        return InMemorySessionService()


# Single runner instance — initialized at app startup
_runner: Runner = None
_session_service = None

def get_runner() -> Runner:
    global _runner
    if _runner is None:
        raise RuntimeError("ADK Runner not initialized. Call init_runner() at startup.")
    return _runner


async def init_runner():
    """Called once at FastAPI app startup (in main.py lifespan)."""
    global _runner, _session_service
    orchestrator = create_pantry_mind_orchestrator()
    _session_service = get_session_service()
    _runner = Runner(
        agent=orchestrator,
        app_name=APP_NAME,
        session_service=_session_service,
        auto_create_session=True
    )


async def run_agent_streaming(
    user_id: str,
    session_id: str,
    message: str,
    image_data: bytes = None     # For receipt scanning — optional image bytes
):
    """
    Async generator that yields streaming events from the ADK runner.
    Consumed by the SSE endpoint in routers/agent.py.

    Yields dicts:
      {"type": "token",     "data": "Hello"}            — text chunk
      {"type": "tool_call", "data": "find"}             — tool being called
      {"type": "agent",     "data": "kitchen_chef_agent"} — agent transfer
      {"type": "done",      "data": ""}                 — final response complete
    """
    if not image_data and os.getenv("ADK_FAST_PATH_ENABLED", "true").lower() == "true":
        try:
            fast_events = await try_fast_path(user_id, message)
        except Exception as fast_err:
            logger.warning("Fast path skipped; falling back to ADK router: %s", fast_err)
            fast_events = None

        if fast_events:
            final_text = " ".join(
                event.get("data", "")
                for event in fast_events
                if event.get("type") == "token"
            )
            asyncio.create_task(trace_session_start(session_id, user_id, message))
            if final_text:
                asyncio.create_task(trace_final_response(session_id, "fast_path", final_text[:200]))
            for event in fast_events:
                yield event
            return

    runner = get_runner()

    # ── Step A: Trace session start ───────────────────────────────────
    await trace_session_start(session_id, user_id, message)

    # ── Step B: Inject relevant memories ──────────────────────────────
    memory_context = ""
    if os.getenv("ADK_MEMORY_ENABLED", "true").lower() == "true":
        try:
            memory_context = await asyncio.wait_for(
                retrieve_relevant_memories(user_id, message),
                timeout=float(os.getenv("ADK_MEMORY_TIMEOUT_SECONDS", "1.25")),
            )
        except Exception as memory_err:
            logger.warning("Skipping memory recall for fast agent response: %s", memory_err)
    memory_hits = len(memory_context.strip().splitlines()) if memory_context else 0
    if memory_hits:
        await trace_memory_recall(session_id, user_id, message[:80], memory_hits)

    user_context = (
        "SYSTEM CONTEXT: The authenticated PantryMind user_id is "
        f"'{user_id}'. Every database query must filter user_id to exactly "
        "this value. Never read or modify another user's records."
    )
    if memory_context and not image_data:
        full_message = f"{user_context}\n\n{memory_context}\n\n---\nUSER MESSAGE: {message}"
    else:
        full_message = f"{user_context}\n\nUSER MESSAGE: {message}"

    # Build the message content
    if image_data:
        # Multimodal message for receipt scanning
        parts = [
            Part(inline_data={"mime_type": "image/jpeg", "data": image_data}),
            Part(text=message or "Scan this receipt and add everything to my pantry.")
        ]
    else:
        parts = [Part(text=full_message)]

    new_message = Content(role="user", parts=parts)

    # ── Step C: Collect history for post-session summarization ────────
    collected_turns = []
    last_agent = "pantrymind_orchestrator"

    # ADK streaming loop
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=new_message
    ):
        # (debug print kept for development, can be removed before submission)
        pass  # print("ADK EVENT TYPE:", type(event))
        current_agent = getattr(event, 'author', None) or "pantrymind_orchestrator"

        # Yield tool calls as status updates (shows agent thinking in UI)
        if event.get_function_calls():
            for fc in event.get_function_calls():
                # Trace tool call
                asyncio.create_task(trace_tool_call(
                    session_id, current_agent, fc.name,
                    str(fc.args)[:200] if fc.args else ""
                ))
                yield {
                    "type": "tool_call",
                    "data": fc.name,
                    "agent": current_agent
                }

        # Yield agent transfer events
        if current_agent != "pantrymind_orchestrator" and current_agent != last_agent:
            asyncio.create_task(trace_agent_transfer(session_id, last_agent, current_agent))
            last_agent = current_agent
            yield {"type": "agent", "data": current_agent}

        # Yield streaming text tokens
        if event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, 'text') and part.text:
                    collected_turns.append({
                        "role":    current_agent,
                        "content": part.text
                    })
                    yield {"type": "token", "data": part.text}

        # Final response
        if event.is_final_response():
            # Gather final response text
            final_text = " ".join(
                turn["content"]
                for turn in collected_turns
                if isinstance(turn, dict) and turn.get("content")
            )

            asyncio.create_task(trace_final_response(session_id, current_agent, final_text[:200]))

            yield {"type": "done", "data": ""}

            # ── Step D: Summarize session in background ──────────────
            full_history = [{"role": "user", "content": message}] + collected_turns
            asyncio.create_task(
                summarize_and_store_session(user_id, session_id, full_history)
            )
            break
