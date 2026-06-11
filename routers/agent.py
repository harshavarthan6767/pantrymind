import json
import asyncio
from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from adk.runner import run_agent_streaming

router = APIRouter(prefix="/api/agent", tags=["Agent"])


@router.post("/chat")
async def agent_chat_stream(
    message: str = Form(...),
    user_id: str = Form(default="default_user"),
    session_id: str = Form(default="default_session"),
    image: UploadFile = File(default=None)    # Optional: for receipt scanning
):
    """
    Unified streaming agent endpoint.
    
    Replaces:
      POST /api/chat
      POST /api/kitchen/chat  
      POST /api/finance/chat

    Returns Server-Sent Events (SSE) stream.
    Frontend listens with EventSource or fetch + ReadableStream.

    SSE Event format:
      data: {"type": "token", "data": "Hello"}
      data: {"type": "tool_call", "data": "find", "agent": "pantry_agent"}
      data: {"type": "agent", "data": "kitchen_chef_agent"}
      data: {"type": "done", "data": ""}
    """
    image_data = None
    if image:
        image_data = await image.read()

    async def event_generator():
        try:
            async for event in run_agent_streaming(
                user_id=user_id,
                session_id=session_id,
                message=message,
                image_data=image_data
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            error_event = {"type": "error", "data": str(e)}
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":               "no-cache",
            "Connection":                  "keep-alive",
            "X-Accel-Buffering":           "no",   # Disable nginx buffering
            "Access-Control-Allow-Origin": "*"
        }
    )


@router.get("/sessions/{session_id}/history")
async def get_session_history(
    session_id: str,
    user_id: str = "default_user"
):
    """Get full conversation history for a session."""
    from adk.runner import _session_service, APP_NAME
    session = await _session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id
    )
    return {
        "session_id": session_id,
        "messages": [
            {"role": m.role, "content": m.parts[0].text if m.parts else ""}
            for m in (session.history if session else [])
        ]
    }
