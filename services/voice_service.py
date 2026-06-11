import os
import json
import re
import logging
import asyncio
import base64
from fastapi import WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError

from google.genai import types as genai_types
from google import genai
from adk.runner import run_agent_streaming
from agents.ordering_tools import simulate_platform_order

logger = logging.getLogger("pantrymind.global_voice")

GLOBAL_VOICE_PROMPT = """\
You are the live voice of PantryMind. Be conversational, concise, and helpful.
When the user asks to plan a meal, do not over-question. If they provide a goal
such as high protein, low carb, South Indian, calorie target, or "use my
inventory", plan from what you know and make reasonable assumptions. Ask only
one short clarifying question when a missing constraint is safety-critical.
For any request involving the user's inventory, finances, nutrition, expiry,
shopping, receipts, analytics, or actions, ALWAYS call delegate_to_pantrymind.
The tool result is also displayed in the desktop side panel. Give a short spoken
summary by default. If the user explicitly asks to "list them all", "read all",
or otherwise requests every item aloud, speak the complete result.
Never speak or print JSON, tool_calls, function call arguments, or code blocks.
If you need PantryMind data, call delegate_to_pantrymind silently and then speak
the natural-language result.
Never claim you cannot access a PantryMind domain before trying the tool.
If delegate_to_pantrymind returns output, treat that output as authoritative.
Do not apologize or ask the user to manually list items after a successful tool response.
When a meal or recipe is created from the tool, speak a brief appetizing summary
of the dish and mention how many steps it has. The side panel will show the full
recipe card automatically.
If the tool result mentions missing or out-of-stock ingredients, tell the user
they can tap the Buy button on the side panel to order them.
"""

DELEGATE_TOOL = genai_types.FunctionDeclaration(
    name="delegate_to_pantrymind",
    description="Delegates a query to the PantryMind Root Agent which has access to Inventory, Finance, Dietary, and Analytics agents. Use this whenever you need to fetch user data or perform an action.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "query": genai_types.Schema(
                type=genai_types.Type.STRING,
                description="The exact query to pass to the agent system.",
            )
        },
        required=["query"],
    ),
)


class LiveSessionRefresh(Exception):
    """Raised when the Live API stream asks us to reopen the engine."""


def _is_normal_live_refresh(exc: Exception) -> bool:
    text = str(exc).lower()
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    return code == 1000 or ("1000" in text and "operation was cancelled" in text)


def _query_mentions(query: str, keywords: tuple[str, ...]) -> bool:
    normalized = query.lower()
    return any(keyword in normalized for keyword in keywords)


def _is_meal_query(query: str) -> bool:
    return _query_mentions(
        query,
        (
            "meal", "cook", "recipe", "breakfast", "lunch", "dinner", "snack",
            "prepare", "make", "high protein", "low carb", "south indian",
            "kitchen", "calorie", "protein",
        ),
    )


def _should_delegate_query(query: str) -> bool:
    return _query_mentions(
        query,
        (
            "inventory", "pantry", "fridge", "what do i have", "what are there",
            "what's there", "stock", "items", "ingredients", "meal", "cook",
            "recipe", "breakfast", "lunch", "dinner", "snack", "prepare",
            "make", "shopping", "receipt", "finance", "spend", "expense",
            "expiry", "expired", "nutrition", "calorie", "protein",
        ),
    )


def _status_for_query(query: str) -> str:
    if _is_meal_query(query):
        return "Cooking..."
    if _query_mentions(query, ("shopping", "grocery", "buy")):
        return "Building shopping list..."
    if _query_mentions(query, ("finance", "spend", "expense", "budget")):
        return "Checking finances..."
    return "Checking PantryMind..."


def _looks_like_tool_json(text: str) -> bool:
    normalized = str(text or "").lower()
    return (
        '"tool_calls"' in normalized
        or "delegate_to_pantrymind" in normalized
        or '"function_call"' in normalized
        or '"arguments"' in normalized and '"name"' in normalized
    )


def _coerce_delegate_query(args: dict) -> str:
    if not isinstance(args, dict):
        return ""

    query = str(args.get("query") or "").strip()
    if query:
        return query

    func = str(args.get("func") or args.get("action") or "").strip()
    params = args.get("params") if isinstance(args.get("params"), dict) else {}
    if func == "plan_meal":
        preferences = params.get("dietary_preferences") or params.get("preferences") or []
        if isinstance(preferences, str):
            preferences = [preferences]
        preference_text = ", ".join(str(item) for item in preferences if item)
        calorie_target = params.get("calorie_target") or params.get("calories")
        pieces = ["Prepare a meal from my inventory"]
        if preference_text:
            pieces.append(f"with {preference_text}")
        if calorie_target:
            pieces.append(f"around {calorie_target} calories")
        return " ".join(pieces) + "."

    if func:
        return f"Run PantryMind action {func} with parameters: {json.dumps(params, ensure_ascii=False)}"

    return json.dumps(args, ensure_ascii=False)


def _format_inventory_context(context: dict) -> str:
    if context.get("status") == "empty":
        return context.get("summary") or "Your pantry is empty. Scan a receipt to add inventory."

    lines = [f"You currently have {context.get('total_items', 0)} active inventory items."]

    expired = context.get("expired") or []
    if expired:
        lines.append("Expired: " + ", ".join(item["name"] for item in expired[:8]))

    expiring = context.get("expiring_soon") or []
    if expiring:
        lines.append("Expiring soon: " + ", ".join(item["name"] for item in expiring[:8]))

    categories = context.get("categories") or {}
    for category, items in sorted(categories.items()):
        names = []
        for item in items[:12]:
            names.append(f"{item['name']} ({item.get('quantity', 0)} {item.get('unit', 'items')})")
        if names:
            lines.append(f"{category}: " + ", ".join(names))

    return "\n".join(lines)


RECIPE_EXTRACTION_PROMPT = """\
You are a JSON formatter. The user will give you a text response about a meal or recipe.
Extract ONLY the structured data and output it in this exact format.
Do NOT add any commentary, explanation, or markdown outside the blocks.

If a recipe/meal plan is present, output:
:::recipe
{
  "meal_name": "Name of the dish",
  "meal_type": "breakfast|lunch|dinner|snack",
  "ingredients": [
    {"amount": "200g", "name": "Chicken Breast", "note": "diced"}
  ],
  "steps": ["Step 1 text", "Step 2 text"],
  "nutrition": {"calories": 450, "protein": "35g", "carbs": "40g", "fat": "12g"},
  "tip": "Optional cooking tip"
}
:::

If there are missing/out-of-stock ingredients that the user doesn't have, also output:
:::order_confirm
{
  "missing_items": [
    {"name": "Soy Sauce", "quantity": "2 tbsp", "reason": "Not in pantry"}
  ],
  "message": "Some ingredients are missing from your pantry."
}
:::

Also include any remaining plain text summary BEFORE the blocks.
If the text is not about a meal/recipe, output the text unchanged with no blocks.
"""


async def _extract_recipe_structured(gemini_client, raw_text: str) -> str:
    """Post-process a plain-text agent result about meals into structured :::recipe::: blocks."""
    if not gemini_client or not raw_text:
        return raw_text

    try:
        model_name = "gemini-3.1-pro"
        full_prompt = f"{RECIPE_EXTRACTION_PROMPT}\n\n---\nTEXT TO FORMAT:\n{raw_text}"
        from services.llm_client import call_gemini_with_retry
        response = await call_gemini_with_retry(lambda: gemini_client.aio.models.generate_content(
            model=model_name,
            contents=full_prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.1,
            )
        ))
        formatted = response.text.strip()
        if ":::recipe" in formatted:
            return formatted
        return raw_text
    except Exception as e:
        logger.warning("Recipe extraction post-processor failed: %s", e)
        return raw_text


async def _direct_delegate_fallback(query: str, user_id: str) -> str | None:
    inventory_keywords = (
        "inventory", "pantry", "fridge", "what do i have", "what are there",
        "what's there", "stock", "items", "ingredients"
    )
    meal_keywords = (
        "meal", "cook", "recipe", "breakfast", "lunch", "dinner", "snack",
        "prepare", "make"
    )

    if not _query_mentions(query, inventory_keywords + meal_keywords):
        return None

    from adk.tools.smart_inventory import get_smart_inventory_context

    context = await get_smart_inventory_context(user_id)
    inventory_text = _format_inventory_context(context)

    if _query_mentions(query, meal_keywords):
        return (
            f"{inventory_text}\n\n"
            "Meal planning fallback: I can read your pantry, but the full chef agent "
            "is temporarily unavailable. Pick a meal type or calorie target and I can "
            "try again, or use these listed ingredients manually."
        )

    return inventory_text


class GlobalVoiceService:
    def __init__(self, gemini_client=None):
        if gemini_client:
            self.gemini = gemini_client
        else:
            use_vertex = os.getenv("GEMINI_BACKEND", "").lower() == "vertex"
            if use_vertex:
                self.gemini = genai.Client(
                    vertexai=True,
                    project=os.getenv("GOOGLE_CLOUD_PROJECT"),
                    location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
                )
            else:
                self.gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    async def handle_live_session(self, websocket: WebSocket, session_id: str, user_id: str):
        logger.info(f"Starting Global Live API session {session_id}")

        tools_disabled = os.getenv("VOICE_DISABLE_TOOLS", "false").lower() == "true"
        active_tools = None
        if not tools_disabled:
            active_tools = [genai_types.Tool(function_declarations=[DELEGATE_TOOL])]

        config = genai_types.LiveConnectConfig(
            system_instruction=genai_types.Content(parts=[genai_types.Part.from_text(text=GLOBAL_VOICE_PROMPT)]),
            tools=active_tools,
            response_modalities=["AUDIO"],
            input_audio_transcription=genai_types.AudioTranscriptionConfig(),
            output_audio_transcription=genai_types.AudioTranscriptionConfig(),
            speech_config=genai_types.SpeechConfig(
                voice_config=genai_types.VoiceConfig(
                    prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(voice_name="Puck")
                )
            )
        )

        model_name = os.getenv(
            "GEMINI_LIVE_MODEL",
            "gemini-live-3.1-pro-native-audio",
        )
        
        try:
            init_msg_raw = await websocket.receive_text()
            init_msg = json.loads(init_msg_raw)
            if init_msg.get("type") == "init":
                logger.info("Frontend initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to receive init from frontend: {e}")
            await websocket.close(code=1011, reason="Init failed")
            return

        stop_event = asyncio.Event()
        audio_queue = asyncio.Queue(maxsize=96)
        voice_state = {
            "assistant_turn_open": False,
            "gemini_activity_since_user_final": False,
            "delegate_started_since_user_final": False,
            "pending_direct_delegate_task": None,
            "pending_text_fallback_task": None,
            "last_user_transcript": "",
            "last_assistant_output": "",
            "delegate_ran_this_turn": False,
        }

        async def send_frontend(payload):
            if stop_event.is_set():
                return
            try:
                await websocket.send_json(payload)
            except Exception:
                stop_event.set()
                raise

        async def queue_audio(payload):
            try:
                pcm_data = base64.b64decode(payload["data"])
            except Exception as decode_err:
                logger.warning("Dropping malformed voice audio packet: %s", decode_err)
                return

            if audio_queue.full():
                try:
                    audio_queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass

            await audio_queue.put({
                "type": "audio",
                "data": pcm_data,
                "mime_type": payload.get("mime_type", "audio/pcm;rate=16000"),
            })

        async def queue_text_input(text: str):
            clean_text = " ".join(str(text or "").split())
            if not clean_text:
                return

            if audio_queue.full():
                try:
                    audio_queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass

            await audio_queue.put({
                "type": "text",
                "text": clean_text,
            })

        def mark_gemini_activity():
            voice_state["gemini_activity_since_user_final"] = True

        async def run_delegate_query(query: str):
            clean_query = " ".join(str(query or "").split())
            if not clean_query:
                return "I did not catch the request clearly."

            voice_state["delegate_started_since_user_final"] = True
            voice_state["delegate_ran_this_turn"] = True
            await send_frontend({
                "type": "status",
                "status": "thinking",
                "message": _status_for_query(clean_query),
            })

            try:
                result_parts = []

                async def collect_agent_result():
                    async for event in run_agent_streaming(
                        user_id=user_id,
                        session_id=session_id,
                        message=clean_query,
                    ):
                        event_type = event.get("type")
                        if event_type == "token":
                            result_parts.append(event.get("data", ""))
                        elif event_type in {"agent", "tool_call"}:
                            await send_frontend({
                                **event,
                                "type": "agent_activity",
                                "activity_type": event_type,
                            })

                await asyncio.wait_for(collect_agent_result(), timeout=45)
                result_str = "".join(result_parts).strip()
                if not result_str:
                    result_str = "PantryMind completed the request but returned no text."
            except Exception as ag_err:
                logger.error("Voice delegation failed: %s", ag_err, exc_info=True)
                fallback = await _direct_delegate_fallback(clean_query, user_id)
                if fallback:
                    result_str = fallback
                else:
                    result_str = f"Agent error: {ag_err}"

            # Post-process: if the query was meal-related, format as structured recipe blocks
            if _is_meal_query(clean_query) and ":::recipe" not in result_str:
                try:
                    formatted = await _extract_recipe_structured(self.gemini, result_str)
                    if formatted and formatted != result_str:
                        result_str = formatted
                        logger.info("Post-processed meal result into structured recipe blocks")
                except Exception as fmt_err:
                    logger.warning("Recipe post-processing failed: %s", fmt_err)

            await send_frontend({
                "type": "agent_result",
                "query": clean_query,
                "text": result_str,
            })
            return result_str

        def schedule_direct_delegate_guard(query: str):
            clean_query = " ".join(str(query or "").split())
            if not clean_query or not _should_delegate_query(clean_query):
                return

            pending = voice_state.get("pending_direct_delegate_task")
            if pending and not pending.done():
                pending.cancel()

            voice_state["delegate_started_since_user_final"] = False

            async def delayed_delegate():
                delay = float(os.getenv("VOICE_DIRECT_DELEGATE_DELAY_SECONDS", "2.2"))
                try:
                    await asyncio.sleep(max(0.6, delay))
                    if stop_event.is_set() or voice_state.get("delegate_started_since_user_final"):
                        return

                    logger.info("Running direct voice delegation guard for query: %s", clean_query)
                    await run_delegate_query(clean_query)
                except asyncio.CancelledError:
                    pass
                except Exception as delegate_err:
                    logger.warning("Voice direct delegation guard failed: %s", delegate_err, exc_info=True)

            voice_state["pending_direct_delegate_task"] = asyncio.create_task(delayed_delegate())

        def schedule_text_fallback(text: str):
            if os.getenv("VOICE_TEXT_FALLBACK", "true").lower() == "false":
                return

            clean_text = " ".join(str(text or "").split())
            if not clean_text:
                return

            pending = voice_state.get("pending_text_fallback_task")
            if pending and not pending.done():
                pending.cancel()

            voice_state["gemini_activity_since_user_final"] = False

            async def delayed_fallback():
                delay = float(os.getenv("VOICE_TEXT_FALLBACK_DELAY_SECONDS", "1.0"))
                try:
                    await asyncio.sleep(max(0.2, delay))
                    if stop_event.is_set() or voice_state.get("gemini_activity_since_user_final"):
                        return

                    logger.info("Using browser transcript fallback for live voice turn.")
                    await send_frontend({
                        "type": "status",
                        "status": "thinking",
                        "message": "Using transcript backup..."
                    })
                    await queue_text_input(clean_text)
                except asyncio.CancelledError:
                    pass
                except Exception as fallback_err:
                    logger.warning("Voice transcript fallback failed: %s", fallback_err)

            voice_state["pending_text_fallback_task"] = asyncio.create_task(delayed_fallback())

        async def execute_voice_order(items: list):
            """Handle ordering missing ingredients directly via WebSocket."""
            try:
                await send_frontend({
                    "type": "status",
                    "status": "thinking",
                    "message": "Placing order..."
                })
                from services.db_service import get_db
                db = await get_db()
                result = await simulate_platform_order(db, user_id, items)
                await send_frontend({
                    "type": "order_result",
                    "success": result.get("success", False),
                    "total": result.get("total_amount", 0),
                    "items_added": result.get("items_added", []),
                    "ledger_id": result.get("ledger_id", ""),
                    "message": result.get("message", "Order completed."),
                    "currency": result.get("currency", "INR"),
                })
                logger.info("Voice order completed: %s", result.get("message"))
            except Exception as order_err:
                logger.error("Voice order failed: %s", order_err, exc_info=True)
                await send_frontend({
                    "type": "order_result",
                    "success": False,
                    "message": f"Order failed: {order_err}",
                })

        async def receive_from_websocket():
            try:
                while not stop_event.is_set():
                    raw = await websocket.receive_text()
                    try:
                        payload = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    if payload.get("type") == "audio":
                        await queue_audio(payload)
                    elif payload.get("type") == "user_speech_final":
                        await send_frontend({
                            "type": "status",
                            "status": "thinking",
                            "message": _status_for_query(payload.get("transcript", ""))
                        })
                        schedule_direct_delegate_guard(payload.get("transcript", ""))
                        schedule_text_fallback(payload.get("transcript", ""))
                    elif payload.get("type") == "voice_order":
                        order_items = payload.get("items", [])
                        if order_items:
                            asyncio.create_task(execute_voice_order(order_items))
                    elif payload.get("type") == "audio_stream_end":
                        await audio_queue.put({"type": "audio_stream_end"})
            except WebSocketDisconnect:
                logger.info("Frontend disconnected")
            except Exception as e:
                logger.error("Frontend receive loop error: %s", e, exc_info=True)
            finally:
                stop_event.set()

        async def send_audio_to_gemini(session):
            while not stop_event.is_set():
                payload = await audio_queue.get()
                if payload.get("type") == "audio_stream_end":
                    await session.send_realtime_input(audio_stream_end=True)
                    continue
                if payload.get("type") == "text":
                    try:
                        await session.send_realtime_input(text=payload["text"])
                    except Exception:
                        try:
                            audio_queue.put_nowait(payload)
                        except asyncio.QueueFull:
                            pass
                        raise
                    continue

                try:
                    await session.send_realtime_input(
                        audio=genai_types.Blob(
                            data=payload["data"],
                            mime_type=payload["mime_type"],
                        )
                    )
                except AttributeError:
                    await session.send(input={"mime_type": "audio/pcm", "data": payload["data"]})

        async def receive_from_gemini(session):
            try:
                while not stop_event.is_set():
                    async for msg in session.receive():
                                
                        # Handle Barge-In (Interruption)
                        server_content = getattr(msg, "server_content", None)
                        if server_content and getattr(server_content, "interrupted", False):
                            logger.info("Gemini detected barge-in (interruption).")
                            mark_gemini_activity()
                            voice_state["assistant_turn_open"] = False
                            await send_frontend({"type": "interrupted"})
                            continue

                        # Handle Connection Setup
                        setup_complete = getattr(msg, "setup_complete", None)
                        if setup_complete:
                            await send_frontend({"type": "status", "status": "listening", "message": "Listening..."})
                            continue

                        # Handle Tool Calls
                        tool_call = getattr(msg, "tool_call", None)
                        if tool_call:
                            mark_gemini_activity()
                            for function_call in tool_call.function_calls:
                                if function_call.name == "delegate_to_pantrymind":
                                    query = _coerce_delegate_query(function_call.args)
                                    result_str = await run_delegate_query(query)
                                    await session.send_tool_response(
                                        function_responses=[
                                            genai_types.FunctionResponse(
                                                id=function_call.id,
                                                name=function_call.name,
                                                response={
                                                    "output": result_str,
                                                    "result": result_str,
                                                },
                                            )
                                        ]
                                    )
                                
                        # Handle Audio and Text output
                        if not server_content:
                            continue

                        model_turn = getattr(server_content, "model_turn", None)
                        if model_turn and getattr(model_turn, "parts", None):
                            mark_gemini_activity()
                            for part in model_turn.parts:
                                inline_data = getattr(part, "inline_data", None)
                                text = getattr(part, "text", None)
                                
                                if text and not _looks_like_tool_json(text):
                                    await send_frontend({"type": "partial_text", "text": text})
                                if inline_data:
                                    voice_state["assistant_turn_open"] = True
                                    b64_audio = base64.b64encode(inline_data.data).decode("utf-8")
                                    await send_frontend({
                                        "type": "audio",
                                        "data": b64_audio,
                                        "mime_type": getattr(inline_data, "mime_type", "audio/pcm;rate=24000")
                                    })

                        input_transcription = getattr(server_content, "input_transcription", None)
                        if input_transcription and getattr(input_transcription, "text", None):
                            mark_gemini_activity()
                            user_text = input_transcription.text.strip()
                            voice_state["last_user_transcript"] = user_text
                            voice_state["delegate_ran_this_turn"] = False
                            voice_state["last_assistant_output"] = ""  # reset for new turn
                            await send_frontend({
                                "type": "user_transcript",
                                "text": user_text,
                            })
                            # Also trigger the delegate guard from Gemini's own transcription
                            schedule_direct_delegate_guard(user_text)

                        output_transcription = getattr(server_content, "output_transcription", None)
                        if output_transcription and getattr(output_transcription, "text", None):
                            mark_gemini_activity()
                            out_text = output_transcription.text
                            voice_state["last_assistant_output"] += " " + out_text
                            if not _looks_like_tool_json(out_text):
                                await send_frontend({
                                    "type": "partial_text",
                                    "text": out_text,
                                })

                        if getattr(server_content, "turn_complete", False):
                            if voice_state.get("user_turn_pending") and not voice_state.get("assistant_turn_open"):
                                logger.debug("Ignoring empty Gemini turn_complete while user turn is pending.")
                                continue
                            voice_state["user_turn_pending"] = False
                            voice_state["assistant_turn_open"] = False
                            await send_frontend({"type": "turn_complete"})

                            # POST-TURN SAFETY NET: if Gemini spoke without delegating
                            # but the user asked something that should have been delegated,
                            # auto-force a delegation now so the right panel gets populated.
                            #
                            # Check TWO signals:
                            #  1. User's input transcript matches delegation keywords
                            #  2. Gemini's OUTPUT mentions meal/recipe/cooking words
                            #     (catches cases where transcription is garbled but Gemini understood)
                            last_q = voice_state.get("last_user_transcript", "")
                            assistant_out = voice_state.get("last_assistant_output", "")
                            should_delegate_input = last_q and _should_delegate_query(last_q)
                            should_delegate_output = assistant_out and _is_meal_query(assistant_out)

                            if (
                                not voice_state.get("delegate_ran_this_turn")
                                and (should_delegate_input or should_delegate_output)
                            ):
                                # Build the best query: prefer the user's transcript, fall back to
                                # constructing one from the assistant's output
                                delegate_query = last_q if last_q else f"Prepare a meal based on my inventory"
                                logger.info(
                                    "Post-turn safety net: Gemini did not delegate for '%s' (output hint: %s). Auto-delegating now.",
                                    delegate_query[:80],
                                    should_delegate_output,
                                )
                                voice_state["last_user_transcript"] = ""  # consume to avoid re-trigger
                                voice_state["last_assistant_output"] = ""
                                asyncio.create_task(run_delegate_query(delegate_query))

                    logger.debug("Gemini receive turn ended; keeping live voice session open.")
                    await asyncio.sleep(0.05)

            except ConnectionClosedOK as e:
                logger.warning("Gemini Live closed normally; refreshing engine: %s", e)
                if stop_event.is_set():
                    return
                raise LiveSessionRefresh(str(e)) from e
            except ConnectionClosedError as e:
                logger.warning("Gemini Live closed with error; refreshing engine: %s", e)
                if stop_event.is_set():
                    return
                raise
            except Exception as e:
                if _is_normal_live_refresh(e):
                    logger.info("Gemini Live stream ended; refreshing engine: %s", e)
                    if stop_event.is_set():
                        return
                    raise LiveSessionRefresh(str(e)) from e
                logger.error("Gemini receive loop error: %s", e, exc_info=True)
                raise

        async def run_gemini_engine():
            reconnect_delay = 0.5
            while not stop_event.is_set():
                try:
                    async with self.gemini.aio.live.connect(model=model_name, config=config) as session:
                        logger.info("Connected to Gemini Global Live API")
                        reconnect_delay = 0.5
                        sender_task = asyncio.create_task(send_audio_to_gemini(session))
                        receiver_task = asyncio.create_task(receive_from_gemini(session))
                        engine_failed = False

                        done, pending = await asyncio.wait(
                            [sender_task, receiver_task],
                            return_when=asyncio.FIRST_COMPLETED,
                        )

                        for task in done:
                            try:
                                task.result()
                            except asyncio.CancelledError:
                                pass
                            except LiveSessionRefresh as task_refresh:
                                logger.info("Gemini engine refresh requested: %s", task_refresh)
                            except Exception as task_err:
                                engine_failed = True
                                logger.warning("Gemini engine task ended: %s", task_err)

                        for task in pending:
                            task.cancel()
                        await asyncio.gather(*pending, return_exceptions=True)

                        if engine_failed and voice_state["assistant_turn_open"] and not stop_event.is_set():
                            voice_state["assistant_turn_open"] = False
                            await send_frontend({
                                "type": "audio_stalled",
                                "message": "Voice engine refreshed mid-response; listening again."
                            })
                except Exception as e:
                    if stop_event.is_set():
                        break
                    logger.warning("Gemini engine reconnect required: %s", e)

                if not stop_event.is_set():
                    await asyncio.sleep(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 2, 4)

        try:
            gemini_task = asyncio.create_task(run_gemini_engine())
            ws_task = asyncio.create_task(receive_from_websocket())

            done, pending = await asyncio.wait([gemini_task, ws_task], return_when=asyncio.FIRST_COMPLETED)
            stop_event.set()
            pending_fallback = voice_state.get("pending_text_fallback_task")
            if pending_fallback and not pending_fallback.done():
                pending_fallback.cancel()
            pending_delegate = voice_state.get("pending_direct_delegate_task")
            if pending_delegate and not pending_delegate.done():
                pending_delegate.cancel()
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            logger.info("Global Voice Session cleaned up completely")
        except Exception as e:
            logger.error(f"Global Voice connection failed: {e}", exc_info=True)
