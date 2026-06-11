import os
import json
import logging
import time
from datetime import datetime, timezone
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
import traceback

from google.genai import types as genai_types
from services.llm_client import call_gemini_with_retry
from services.chat_service import extract_and_validate_choice
from agents.kitchen_agent import KITCHEN_SYSTEM_PROMPT, build_kitchen_context
from agents.kitchen_tools.inventory_tools import (
    get_pantry_by_macro_role,
    search_inventory,
    get_expiring_items,
    get_user_kitchen_profile,
    optimize_meal_with_lp,
    log_meal_consumed
)
from agents.ordering_tools import simulate_platform_order
from data.nutrition_db import NUTRITION_DB

logger = logging.getLogger("pantrymind.kitchen_chat")

# ---------------------------------------------------------------------------
# Kitchen Tools Definitions for Gemini
# ---------------------------------------------------------------------------

GET_PANTRY_BY_MACRO_ROLE_TOOL = genai_types.FunctionDeclaration(
    name="get_pantry_by_macro_role",
    description="Query the pantry inventory by nutritional macro role. Use this before suggesting ingredients.",
    parameters=genai_types.Schema(
        type="OBJECT",
        properties={
            "role": genai_types.Schema(
                type="STRING",
                description="The macro role to query. Valid: protein, carbohydrate, vegetable, fat, flavoring, grain, dairy"
            ),
            "dietary_preference": genai_types.Schema(
                type="STRING",
                description="Optional. Restrict by diet: VEG, VEGAN, NON_VEG, KETO"
            ),
        },
        required=["role"]
    )
)

SEARCH_INVENTORY_TOOL = genai_types.FunctionDeclaration(
    name="search_inventory",
    description="Flexible inventory search. Query by category, sub_category, dietary_flag, or name substring. Use this for general inventory browsing, checking if specific items exist, or filtering by any combination of attributes. If no filters are given, returns the full available inventory.",
    parameters=genai_types.Schema(
        type="OBJECT",
        properties={
            "category": genai_types.Schema(
                type="STRING",
                description="Filter by category. Valid: PRODUCE, DAIRY_EGGS, MEAT_SEAFOOD, PANTRY_DRY, FROZEN, BAKERY, BEVERAGES, SNACKS, CONDIMENTS, HOUSEHOLD, PERSONAL_CARE, OTHER"
            ),
            "sub_category": genai_types.Schema(
                type="STRING",
                description="Filter by sub-category. E.g. poultry, leafy_greens, rice_pasta, spices_masala, eggs, etc."
            ),
            "dietary_flag": genai_types.Schema(
                type="STRING",
                description="Filter by diet type: VEG, VEGAN, NON_VEG, SEAFOOD, DAIRY, EGG, NA"
            ),
            "name_contains": genai_types.Schema(
                type="STRING",
                description="Search for items whose name contains this substring (case-insensitive). E.g. 'chicken', 'rice', 'tomato'"
            ),
            "limit": genai_types.Schema(
                type="INTEGER",
                description="Max items to return. Default 50."
            ),
        }
    )
)

GET_EXPIRING_ITEMS_TOOL = genai_types.FunctionDeclaration(
    name="get_expiring_items",
    description="Get items expiring within the next few days to prioritize them in meals.",
    parameters=genai_types.Schema(
        type="OBJECT",
        properties={
            "within_days": genai_types.Schema(
                type="INTEGER",
                description="Number of days to look ahead. Default is 3."
            )
        }
    )
)

GET_USER_PROFILE_TOOL = genai_types.FunctionDeclaration(
    name="get_user_kitchen_profile",
    description="Get the user's calorie targets, dietary preferences, and recent meals.",
    parameters=genai_types.Schema(
        type="OBJECT",
        properties={}
    )
)

OPTIMIZE_MEAL_TOOL = genai_types.FunctionDeclaration(
    name="optimize_meal_with_lp",
    description="Calculate exact portion sizes for a list of ingredients to hit specific calorie and macro targets.",
    parameters=genai_types.Schema(
        type="OBJECT",
        properties={
            "ingredients": genai_types.Schema(
                type="ARRAY",
                items=genai_types.Schema(
                    type="OBJECT",
                    properties={
                        "name": genai_types.Schema(type="STRING"),
                        "category": genai_types.Schema(type="STRING"),
                        "quantity": genai_types.Schema(type="NUMBER"),
                        "unit": genai_types.Schema(type="STRING"),
                        "item_id": genai_types.Schema(type="STRING")
                    }
                ),
                description="List of ingredient dictionaries available to use."
            ),
            "targets": genai_types.Schema(
                type="OBJECT",
                properties={
                    "calories": genai_types.Schema(type="INTEGER"),
                    "protein_min": genai_types.Schema(type="INTEGER"),
                    "carbs_max": genai_types.Schema(type="INTEGER"),
                    "fat_max": genai_types.Schema(type="INTEGER")
                },
                description="Target macros for the meal."
            ),
            "meal_type": genai_types.Schema(
                type="STRING",
                description="e.g. breakfast, lunch, dinner, snack"
            )
        },
        required=["ingredients", "targets"]
    )
)

LOG_MEAL_TOOL = genai_types.FunctionDeclaration(
    name="log_meal_consumed",
    description="Record a meal as consumed, updating inventory and nutrition tracking.",
    parameters=genai_types.Schema(
        type="OBJECT",
        properties={
            "meal_plan_id": genai_types.Schema(
                type="STRING",
                description="ID or name of the meal."
            ),
            "items_consumed": genai_types.Schema(
                type="ARRAY",
                items=genai_types.Schema(
                    type="OBJECT",
                    properties={
                        "item_id": genai_types.Schema(type="STRING"),
                        "grams_used": genai_types.Schema(type="NUMBER")
                    }
                ),
                description="List of ingredients consumed with amounts."
            )
        },
        required=["meal_plan_id", "items_consumed"]
    )
)

DELEGATE_ORDERING_TOOL = genai_types.FunctionDeclaration(
    name="delegate_to_ordering_agent",
    description="Delegate purchasing missing ingredients to the Ordering Agent. It will simulate a purchase on a delivery platform, add items to inventory, and log the expense.",
    parameters=genai_types.Schema(
        type="OBJECT",
        properties={
            "ingredients": genai_types.Schema(
                type="ARRAY",
                items=genai_types.Schema(
                    type="OBJECT",
                    properties={
                        "name": genai_types.Schema(type="STRING"),
                        "category": genai_types.Schema(type="STRING", description="Optional category"),
                        "quantity": genai_types.Schema(type="STRING"),
                        "unit": genai_types.Schema(type="STRING"),
                        "reason": genai_types.Schema(type="STRING", description="Reason for ordering")
                    }
                )
            )
        },
        required=["ingredients"]
    )
)

KITCHEN_TOOLS = genai_types.Tool(
    function_declarations=[
        GET_PANTRY_BY_MACRO_ROLE_TOOL,
        SEARCH_INVENTORY_TOOL,
        GET_EXPIRING_ITEMS_TOOL,
        GET_USER_PROFILE_TOOL,
        OPTIMIZE_MEAL_TOOL,
        LOG_MEAL_TOOL,
        DELEGATE_ORDERING_TOOL
    ]
)

class KitchenChatService:
    """
    Dedicated Chat Service for the Kitchen AI Chef.
    """

    def __init__(self, db_service, gemini_client, model_name: str = None):
        self.db = db_service
        self.gemini = gemini_client
        self.model = model_name or os.getenv("GEMINI_MODEL_KITCHEN", os.getenv("GEMINI_MODEL", "gemini-3.1-pro"))

    async def load_history(self, session_id: str, limit: int = 20) -> list[dict]:
        return await self.db.find(
            "kitchen_conversation_history",
            {"session_id": session_id},
            limit=limit,
            sort=[("timestamp", 1)],
        )

    async def save_turn(
        self, session_id: str, role: str, content: str, metadata: dict | None = None
    ) -> None:
        doc = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if metadata:
            doc["metadata"] = metadata
        await self.db.insert_one("kitchen_conversation_history", doc)

    async def _execute_tool_call(self, function_call, user_id: str) -> str:
        name = function_call.name
        args = function_call.args or {}

        try:
            if name == "get_pantry_by_macro_role":
                role = args.get("role")
                diet = args.get("dietary_preference")
                res = await get_pantry_by_macro_role(self.db, user_id, role, diet)
                return json.dumps(res, default=str)

            elif name == "search_inventory":
                res = await search_inventory(
                    self.db, user_id,
                    category=args.get("category"),
                    sub_category=args.get("sub_category"),
                    dietary_flag=args.get("dietary_flag"),
                    name_contains=args.get("name_contains"),
                    limit=int(args.get("limit", 50)),
                )
                return json.dumps(res, default=str)

            elif name == "get_expiring_items":
                days = int(args.get("within_days", 3))
                res = await get_expiring_items(self.db, user_id, days)
                return json.dumps(res, default=str)

            elif name == "get_user_kitchen_profile":
                res = await get_user_kitchen_profile(self.db, user_id)
                return json.dumps(res, default=str)

            elif name == "optimize_meal_with_lp":
                ingredients = args.get("ingredients", [])
                targets = args.get("targets", {})
                meal_type = args.get("meal_type", "dinner")
                
                # Fetch nutrition for USDA misses if needed
                from services.usda_nutrition import get_nutrition_for_items
                names = [i["name"] for i in ingredients]
                nut_data = await get_nutrition_for_items(names)
                
                res = await optimize_meal_with_lp(ingredients, nut_data, targets, meal_type)
                return json.dumps(res, default=str)

            elif name == "log_meal_consumed":
                res = await log_meal_consumed(
                    self.db, user_id,
                    args.get("meal_plan_id"),
                    args.get("items_consumed")
                )
                return json.dumps(res, default=str)

            elif name == "delegate_to_ordering_agent":
                ingredients = args.get("ingredients", [])
                logger.info(f"Ordering {len(ingredients)} items directly (bypassing Ordering Agent LLM)")
                # Call simulate_platform_order directly — no need for a second LLM call
                # self.db is a MongoDBService; ordering_tools needs the raw Motor db
                raw_db = self.db.db if hasattr(self.db, 'db') else self.db
                res = await simulate_platform_order(raw_db, user_id, ingredients)
                logger.info(f"Order complete. Result length: {len(res)}")
                return json.dumps({"status": "Order Complete", "summary": res}, default=str)

            return json.dumps({"error": f"Unknown tool: {name}"})

        except Exception as e:
            logger.error(f"Kitchen Tool execution failed: {e}")
            return json.dumps({"error": f"Tool error: {str(e)}"})

    async def handle_live_session(self, websocket: WebSocket, session_id: str, user_id: str):
        """
        Handles a real-time bidirectional WebSocket connection using Gemini Multimodal Live API.
        """
        logger.info(f"Starting Live API session {session_id} for user {user_id}")
        
        # Load context
        history, context = await asyncio.gather(
            self.load_history(session_id),
            build_kitchen_context(self.db, user_id)
        )
        
        voice_prompt = (
            f"{KITCHEN_SYSTEM_PROMPT}\n\n{context}\n\n"
            "CRITICAL VOICE MODE INSTRUCTIONS:\n"
            "You are participating in a LIVE, REAL-TIME audio conversation. "
            "Keep your answers short, conversational, and natural. "
            "Do NOT output markdown tables, long lists, or JSON blocks. "
            "Always ask for the user's opinion (e.g. 'How does that sound?', 'Would you like to make that?'). "
            "If ingredients are missing, EXPLICITLY ask 'Do you want me to order [missing items] for you?'"
        )
        
        config = genai_types.LiveConnectConfig(
            system_instruction=genai_types.Content(parts=[genai_types.Part.from_text(text=voice_prompt)]),
            tools=[KITCHEN_TOOLS],
            response_modalities=["AUDIO"],
            speech_config=genai_types.SpeechConfig(
                voice_config=genai_types.VoiceConfig(
                    prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(
                        voice_name="Aoede"
                    )
                )
            )
        )
        
        GEMINI_BACKEND = os.getenv("GEMINI_BACKEND", "ai_studio").lower().strip()

        ai_studio_default = "gemini-3.1-pro-native-audio-preview-12-2025"
        model_name = "gemini-3.1-flash-live-preview"

        blocked_models = {
            "gemini-3.1-pro",
            "models/gemini-3.1-pro",
            "gemini-3.1-pro",
            "models/gemini-3.1-pro",
            "gemini-3.1-pro-live-preview",
            "gemini-3.1-pro-live-001",
            "models/gemini-3.1-pro-live-001"
        }

        if model_name in blocked_models:
            model_name = vertex_default if GEMINI_BACKEND == "vertex" else ai_studio_default
            
        logger.info(f"Using Kitchen Gemini backend: {GEMINI_BACKEND}")
        logger.info(f"Using Kitchen Live model: {model_name}")

        # === FIX IS HERE ===
        logger.info("Waiting for frontend init...")
        try:
            # Explicitly wait for the first message from React before talking to Gemini
            init_msg_raw = await websocket.receive_text()
            init_msg = json.loads(init_msg_raw)
            if init_msg.get("type") == "init":
                logger.info(f"Frontend initialized successfully: {init_msg}")
            else:
                logger.warning(f"Expected init, but got: {init_msg}")
        except Exception as e:
            logger.error(f"Failed to receive init from frontend: {e}")
            await websocket.close(code=1011, reason="Failed to initialize")
            return
        # ===================

        try:
            async with self.gemini.aio.live.connect(model=model_name, config=config) as session:
                logger.info("Connected to Gemini Kitchen Live API")
                
                # Send history if available
                if history:
                    hist_str = "\n".join([f"{m['role']}: {m['content']}" for m in history])
                    await session.send(input=f"Here is our conversation history so far:\n{hist_str}", end_of_turn=True)
            
            async def receive_from_websocket():
                """Reads PCM audio chunks from frontend and sends them to Gemini."""
                try:
                    while True:
                        data = await websocket.receive_text()
                        # data is base64 encoded PCM from frontend
                        try:
                            pcm_data = base64.b64decode(data)
                            try:
                                await session.send_realtime_input(
                                    audio=genai_types.Blob(
                                        data=pcm_data,
                                        mime_type="audio/pcm;rate=16000"
                                    )
                                )
                            except AttributeError:
                                # Fallback if SDK doesn't support send_realtime_input
                                await session.send(input={"mime_type": "audio/pcm", "data": pcm_data})
                        except Exception as e:
                            logger.error(f"Error sending audio to Gemini: {e}")
                except WebSocketDisconnect:
                    logger.info("Frontend disconnected")
                except Exception as e:
                    logger.error(f"Receive loop error: {e}")
            
            async def receive_from_gemini():
                """Reads ServerContent from Gemini and routes Audio to Frontend or Tools to execution."""
                try:
                    async for msg in session.receive():
                        server_content = getattr(msg, "server_content", None)
                        
                        # Handle Barge-In (Interruption)
                        if server_content and getattr(server_content, "interrupted", False):
                            logger.info("Kitchen Gemini detected barge-in (interruption).")
                            await websocket.send_json({"type": "interrupted"})
                            continue

                        if not server_content:
                            continue
                            
                        # Handle audio output
                        model_turn = server_content.model_turn
                        if model_turn and model_turn.parts:
                            for part in model_turn.parts:
                                if part.inline_data:
                                    # Send back the raw audio (PCM) over websocket as base64 string
                                    b64_audio = base64.b64encode(part.inline_data.data).decode('utf-8')
                                    await websocket.send_json({"type": "audio", "data": b64_audio})
                                    
                        # Handle function calls
                        if server_content.turn_complete:
                            # Send a signal to frontend that the turn is complete (optional)
                            await websocket.send_json({"type": "turn_complete"})
                            
                        if msg.tool_call:
                            for function_call in msg.tool_call.function_calls:
                                logger.info(f"Live API Tool Call: {function_call.name}")
                                try:
                                    result_str = await self._execute_tool_call(function_call, user_id)
                                    # Send the function response back to Gemini
                                    function_response = genai_types.LiveClientContent(
                                        tool_response=genai_types.LiveClientToolResponse(
                                            function_responses=[
                                                genai_types.FunctionResponse(
                                                    id=function_call.id,
                                                    name=function_call.name,
                                                    response={"result": result_str}
                                                )
                                            ]
                                        )
                                    )
                                    await session.send(input=function_response)
                                except Exception as e:
                                    logger.error(f"Tool execution failed in Live API: {e}")
                except ConnectionClosedOK as e:
                    logger.warning("Gemini Live closed normally: code=%s reason=%s", e.code, e.reason)
                except ConnectionClosedError as e:
                    logger.error("Gemini Live closed with error: code=%s reason=%s", e.code, e.reason)
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    if "1000 None" in str(e):
                        logger.warning("Gemini Live closed cleanly (APIError 1000).")
                    else:
                        logger.error(f"Gemini receive loop error: {e}", exc_info=True)
                        traceback.print_exc()

            # Run both loops concurrently
            gemini_task = asyncio.create_task(receive_from_gemini())
            ws_task = asyncio.create_task(receive_from_websocket())
            
            done, pending = await asyncio.wait(
                [gemini_task, ws_task], 
                return_when=asyncio.FIRST_COMPLETED
            )
            
            for task in pending:
                task.cancel()
            
            await asyncio.gather(*pending, return_exceptions=True)
            logger.info("Kitchen Chat Session cleaned up")
        except Exception as e:
            logger.error(f"Kitchen Voice FATAL ERROR: {type(e).__name__} - {e}", exc_info=True)

    async def process_voice_message(
        self, session_id: str, user_id: str, audio_bytes: bytes, mime_type: str
    ) -> tuple[str, dict, str]:
        t0 = time.time()
        active_model = "gemini-3.1-pro"
        
        metadata = {"model": active_model, "tools_called": [], "intent": "VOICE"}
        
        history, context = await asyncio.gather(
            self.load_history(session_id),
            build_kitchen_context(self.db, user_id)
        )
        
        # Modify prompt slightly for Voice mode: concise, conversational, asks questions back
        voice_prompt = (
            f"{KITCHEN_SYSTEM_PROMPT}\n\n{context}\n\n"
            "CRITICAL VOICE MODE INSTRUCTIONS:\n"
            "You are responding via VOICE. Keep your answers conversational, natural, and CONCISE. "
            "Do NOT output markdown tables, long lists, or JSON blocks. "
            "Always ask for the user's opinion (e.g. 'How does that sound?', 'Would you like to make that?'). "
            "If ingredients are missing, EXPLICITLY ask 'Do you want me to order [missing items] for you?'"
        )
        
        contents = []
        for turn in history:
            role = "user" if turn["role"] == "user" else "model"
            contents.append(
                genai_types.Content(
                    role=role,
                    parts=[genai_types.Part.from_text(text=turn["content"])],
                )
            )

        # Add the audio input from the user
        contents.append(
            genai_types.Content(
                role="user",
                parts=[genai_types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)],
            )
        )
        
        config = genai_types.GenerateContentConfig(
            system_instruction=voice_prompt,
            tools=[KITCHEN_TOOLS],
            temperature=0.4,
            top_p=0.9,
            response_modalities=["AUDIO"],
            speech_config={
                "voice_config": {
                    "prebuilt_voice_config": {
                        "voice_name": "Aoede"
                    }
                }
            }
        )
        
        try:
            response = await call_gemini_with_retry(lambda: self.gemini.aio.models.generate_content(
                model=active_model,
                contents=contents,
                config=config,
            ))
        except Exception as e:
            logger.error(f"Error calling gemini voice: {e}")
            raise
            
        max_rounds = 5
        round_count = 0
        
        while round_count < max_rounds:
            round_count += 1
            candidate = response.candidates[0] if response.candidates else None
            if not candidate or not candidate.content or not candidate.content.parts:
                break

            function_calls = [p for p in candidate.content.parts if p.function_call]
            if not function_calls:
                break

            contents.append(candidate.content)

            response_parts = []
            for fc_part in function_calls:
                fc = fc_part.function_call
                logger.info(f"Kitchen Voice Tool: {fc.name}")

                result_str = await self._execute_tool_call(fc, user_id)
                metadata["tools_called"].append({
                    "name": fc.name,
                    "args": dict(fc.args or {}),
                    "result_preview": result_str[:200],
                })

                response_parts.append(
                    genai_types.Part.from_function_response(
                        name=fc.name,
                        response={"result": result_str},
                    )
                )

            contents.append(
                genai_types.Content(
                    role="user",
                    parts=response_parts,
                )
            )

            response = await call_gemini_with_retry(lambda: self.gemini.aio.models.generate_content(
                model=active_model,
                contents=contents,
                config=config,
            ))

        reply_text = ""
        audio_b64 = None
        
        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if part.text:
                    reply_text += part.text
                if part.inline_data:
                    # Found the generated audio
                    import base64
                    audio_b64 = base64.b64encode(part.inline_data.data).decode("utf-8")

        if not reply_text:
            reply_text = "I'm sorry, I couldn't process that kitchen request."

        # Extract choice block if any (though voice might not output it)
        reply_text, choice = extract_and_validate_choice(reply_text)
        if choice:
            metadata["choice"] = choice

        metadata["latency_ms"] = int((time.time() - t0) * 1000)

        # Log to history
        await asyncio.gather(
            self.save_turn(session_id, "user", "[Voice Input]"),
            self.save_turn(session_id, "assistant", reply_text, metadata),
        )

        return reply_text, metadata, audio_b64

    async def process_message(
        self, session_id: str, user_id: str, user_message: str
    ) -> tuple[str, dict]:
        t0 = time.time()
        
        # 1. Fast Intent Classification
        try:
            intent_response = await call_gemini_with_retry(lambda: self.gemini.aio.models.generate_content(
                model="gemini-3.1-pro",
                contents=f"Classify this message to a kitchen AI as either SIMPLE (small talk, greetings, thanks) or COMPLEX (recipes, meal plans, cooking advice, inventory questions, ordering). Reply with exactly one word: SIMPLE or COMPLEX. Message: {user_message}"
            ))
            intent = intent_response.text.strip().upper()
        except Exception:
            intent = "COMPLEX"
            
        is_simple = "SIMPLE" in intent
        active_model = "gemini-3.1-pro" if is_simple else "gemini-3.1-pro"
        
        metadata = {"model": active_model, "tools_called": [], "intent": intent}

        history, context = await asyncio.gather(
            self.load_history(session_id),
            build_kitchen_context(self.db, user_id)
        )
        
        if is_simple:
            system_prompt = "You are Chef Mira. The user is making small talk or saying hello. Be brief, warm, and friendly. Do not use markdown tables. Limit your response to 1-2 sentences."
            active_tools = None
        else:
            system_prompt = f"{KITCHEN_SYSTEM_PROMPT}\n\n{context}"
            active_tools = [KITCHEN_TOOLS]

        contents = []
        for turn in history:
            role = "user" if turn["role"] == "user" else "model"
            contents.append(
                genai_types.Content(
                    role=role,
                    parts=[genai_types.Part.from_text(text=turn["content"])],
                )
            )

        contents.append(
            genai_types.Content(
                role="user",
                parts=[genai_types.Part.from_text(text=user_message)],
            )
        )

        config = genai_types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=active_tools,
            temperature=0.4,
            top_p=0.9,
        )

        try:
            response = await call_gemini_with_retry(lambda: self.gemini.aio.models.generate_content(
                model=active_model,
                contents=contents,
                config=config,
            ))
        except Exception as e:
            logger.error(f"Error calling gemini: {e}")
            raise

        max_rounds = 5
        round_count = 0

        while round_count < max_rounds:
            round_count += 1
            candidate = response.candidates[0] if response.candidates else None
            if not candidate or not candidate.content or not candidate.content.parts:
                break

            function_calls = [p for p in candidate.content.parts if p.function_call]
            if not function_calls:
                break

            contents.append(candidate.content)

            response_parts = []
            for fc_part in function_calls:
                fc = fc_part.function_call
                logger.info(f"Kitchen Tool: {fc.name}")

                result_str = await self._execute_tool_call(fc, user_id)
                metadata["tools_called"].append({
                    "name": fc.name,
                    "args": dict(fc.args or {}),
                    "result_preview": result_str[:200],
                })

                response_parts.append(
                    genai_types.Part.from_function_response(
                        name=fc.name,
                        response={"result": result_str},
                    )
                )

            contents.append(
                genai_types.Content(
                    role="user",
                    parts=response_parts,
                )
            )

            response = await call_gemini_with_retry(lambda: self.gemini.aio.models.generate_content(
                model=active_model,
                contents=contents,
                config=config,
            ))

        reply = ""
        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if part.text:
                    reply += part.text

        if not reply:
            reply = "I'm sorry, I couldn't process that kitchen request."

        # Extract choice block if any
        reply, choice = extract_and_validate_choice(reply)
        if choice:
            metadata["choice"] = choice

        metadata["latency_ms"] = int((time.time() - t0) * 1000)

        await asyncio.gather(
            self.save_turn(session_id, "user", user_message),
            self.save_turn(session_id, "assistant", reply, metadata),
        )

        return reply, metadata
