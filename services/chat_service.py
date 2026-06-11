"""
PantryMind Chat Service — Conversational AI Engine (Iteration 2)

Architecture:
  User message → Load conversation history → Build system prompt with schema
  → Gemini function-calling → Execute MongoDB query → Feed result back
  → Gemini generates natural language response → Store conversation turn

Uses Gemini's native function-calling (tool_use) to translate natural language
into MongoDB queries, execute them, and synthesize human-readable answers.
"""

import os
import json
import logging
import time
from datetime import datetime, timezone
from services.llm_client import call_gemini_with_retry
import re
from pydantic import BaseModel

from google.genai import types as genai_types

logger = logging.getLogger("pantrymind.chat")

class ChoiceOption(BaseModel):
    id: str
    label: str

class ChoiceBlock(BaseModel):
    options: list[ChoiceOption]
    message: str

def extract_and_validate_choice(raw_response: str) -> tuple:
    """Returns (clean_text, validated_choice_dict | None)."""
    pattern = r'<choice>\s*(.*?)\s*</choice>'
    match = re.search(pattern, raw_response, re.DOTALL)
    if not match:
        return raw_response, None
    try:
        data = json.loads(match.group(1))
        validated = ChoiceBlock(**data)
        clean = re.sub(pattern, '', raw_response, flags=re.DOTALL).strip()
        return clean, validated.model_dump()
    except Exception as e:
        logger.warning(f"Malformed choice block — skipping: {e}")
        # Don't break the response; just remove the broken block
        clean = re.sub(pattern, '', raw_response, flags=re.DOTALL).strip()
        return clean, None

# ---------------------------------------------------------------------------
# MongoDB Schema Registry — injected into the system prompt so Gemini
# understands the exact shape of every collection.
# ---------------------------------------------------------------------------
SCHEMA_DESCRIPTION = """You have access to the user's PantryMind database with these MongoDB collections:

## inventory
Fields: name (str), normalized_name (str), category (str), sub_category (str),
        quantity (float), unit (str), cost_per_unit (float), store (str),
        dietary_flag (str: "VEG"|"VEGAN"|"NON_VEG"|"SEAFOOD"|"DAIRY"|"EGG"|"NA"),
        is_perishable (bool), is_consumed (bool),
        purchase_date (ISO str), expiry_date (ISO str | null),
        safe_expiry_date (ISO str | null),
        status (str: "fresh"|"Fresh"|"expiring"|"Expiring Soon"|"expired"|"Expired"),
        image_url (str), created_at (ISO str)

IMPORTANT category values (UPPERCASE, use EXACTLY as shown):
  PRODUCE, DAIRY_EGGS, MEAT_SEAFOOD, PANTRY_DRY, FROZEN,
  BAKERY, BEVERAGES, SNACKS, CONDIMENTS, HOUSEHOLD,
  PERSONAL_CARE, BABY, PET, OTHER

Common sub_category values:
  For MEAT_SEAFOOD: poultry, red_meat, pork, seafood_fish, processed_deli
  For PRODUCE: leafy_greens, root_vegetables, tropical_fruits, herbs, onion_garlic, tomatoes_peppers
  For DAIRY_EGGS: eggs, milk, yogurt, soft_cheese, hard_cheese, butter_cream
  For PANTRY_DRY: rice_pasta, flour, spices_masala, oils, legumes_pulses, canned_goods

## receipts
Fields: store (str), date (ISO str), total (float), subtotal (float),
        taxes ({CGST: float, SGST: float, IGST: float}),
        item_count (int), status (str), engine (str)

## financial_ledger
Fields: date (ISO str), amount (float), category (str),
        description (str), type (str: "expense"|"income")

## consumption_history
Fields: item_name (str), month_key (str: "YYYY-MM"), consumed_qty (float)

## warranties
Fields: product_name (str), brand (str), purchase_date (ISO str),
        expiry_date (ISO str), store (str)

## carbon_log
Fields: item (str), kg_co2e (float), date (ISO str)

## nutrition_log
Fields: item (str), calories (float), protein_g (float),
        carbs_g (float), fat_g (float), date (ISO str)

## restock_predictions
Fields: item (str), current_qty (float), predicted_empty_date (ISO str)

## user_profile
Fields: user_id (str), name (str), monthly_salary (float),
        tax_regime (str: "new"|"old")
"""

SYSTEM_PROMPT = """You are PantryMind, an intelligent personal household management AI assistant.
You help users manage their pantry inventory, track spending, monitor nutrition,
and make smart grocery decisions.

{schema}

RULES:
1. ALWAYS use the query_database tool to fetch real data. NEVER fabricate numbers or items.
2. For date/time comparisons, today is {current_date}.
3. Use MongoDB aggregation pipelines ($match, $group, $sort, $project, $limit) for complex queries (sums, averages, groupings, top-N).
4. Use "find" operation for simple lookups and listings.
5. Use "count" operation when the user asks "how many".
6. Format currency as ₹X,XXX.XX (Indian Rupees).
7. Be concise but thorough. Use bullet points and tables when appropriate.
8. If data is missing or empty, say so honestly — never invent data.
9. When listing items, show name, quantity, unit, and relevant details.
10. For spending queries, always pull from the financial_ledger collection.
11. For inventory queries, use the inventory collection.
12. String matching in MongoDB queries should be case-insensitive where possible — use $regex with $options: "i".
"""

# ---------------------------------------------------------------------------
# Gemini Function Declarations (Tool Definitions)
# ---------------------------------------------------------------------------
QUERY_DATABASE_TOOL = genai_types.FunctionDeclaration(
    name="query_database",
    description=(
        "Execute a MongoDB query or aggregation pipeline against any PantryMind collection. "
        "Use 'find' for simple lookups, 'aggregate' for complex analytics (sums, counts, groupings), "
        "and 'count' to count matching documents."
    ),
    parameters=genai_types.Schema(
        type="OBJECT",
        properties={
            "collection": genai_types.Schema(
                type="STRING",
                description="The MongoDB collection to query",
                enum=[
                    "inventory", "receipts", "financial_ledger",
                    "consumption_history", "warranties", "carbon_log",
                    "nutrition_log", "restock_predictions", "user_profile",
                ],
            ),
            "operation": genai_types.Schema(
                type="STRING",
                description="The type of query operation",
                enum=["find", "aggregate", "count"],
            ),
            "query": genai_types.Schema(
                type="STRING",
                description=(
                    "For find/count: a JSON string of the MongoDB filter document. "
                    "Example: '{\"category\": \"Groceries\"}'. For aggregate: ignored."
                ),
            ),
            "pipeline": genai_types.Schema(
                type="STRING",
                description=(
                    "For aggregate: a JSON string of the aggregation pipeline array. "
                    "Example: '[{\"$group\": {\"_id\": \"$category\", \"total\": {\"$sum\": \"$amount\"}}}]'. "
                    "For find/count: ignored."
                ),
            ),
            "sort": genai_types.Schema(
                type="STRING",
                description=(
                    "For find: a JSON string of the sort specification. "
                    "Example: '{\"date\": -1}' for descending by date. Optional."
                ),
            ),
            "limit": genai_types.Schema(
                type="INTEGER",
                description="Maximum number of documents to return for find. Default 20.",
            ),
        },
        required=["collection", "operation"],
    ),
)

GET_CURRENT_DATE_TOOL = genai_types.FunctionDeclaration(
    name="get_current_date",
    description="Get the current date and time in ISO format and human-readable format.",
    parameters=genai_types.Schema(
        type="OBJECT",
        properties={},
    ),
)

CHAT_TOOLS = genai_types.Tool(
    function_declarations=[QUERY_DATABASE_TOOL, GET_CURRENT_DATE_TOOL]
)


class ChatService:
    """
    Orchestrates multi-turn conversations between the user and Gemini,
    with function-calling for live MongoDB queries.
    """

    def __init__(self, db_service, gemini_client, model_name: str = None):
        self.db = db_service
        self.gemini = gemini_client
        self.model = model_name or os.getenv("GEMINI_MODEL_CHAT", os.getenv("GEMINI_MODEL", "gemini-3.1-pro"))

    # ------------------------------------------------------------------
    # Conversation History
    # ------------------------------------------------------------------
    async def load_history(self, session_id: str, limit: int = 20) -> list[dict]:
        """Load the last N conversation turns for a session."""
        return await self.db.find(
            "conversation_history",
            {"session_id": session_id},
            limit=limit,
            sort=[("timestamp", 1)],
        )

    async def save_turn(
        self, session_id: str, role: str, content: str, metadata: dict | None = None
    ) -> None:
        """Persist a single conversation turn."""
        doc = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if metadata:
            doc["metadata"] = metadata
        await self.db.insert_one("conversation_history", doc)

    # ------------------------------------------------------------------
    # Tool Execution
    # ------------------------------------------------------------------
    async def _execute_tool_call(self, function_call) -> str:
        """Execute a Gemini function call against MongoDB and return the result as a string."""
        name = function_call.name
        args = function_call.args or {}

        if name == "get_current_date":
            now = datetime.now(timezone.utc)
            return json.dumps({
                "iso": now.isoformat(),
                "human": now.strftime("%A, %B %d, %Y at %I:%M %p UTC"),
            })

        if name == "query_database":
            collection = args.get("collection", "inventory")
            operation = args.get("operation", "find")
            limit = int(args.get("limit", 20))

            try:
                if operation == "find":
                    query = json.loads(args.get("query", "{}"))
                    sort_spec = args.get("sort")
                    sort = None
                    if sort_spec:
                        sort_dict = json.loads(sort_spec)
                        sort = [(k, int(v)) for k, v in sort_dict.items()]
                    results = await self.db.find(
                        collection, query, limit=limit, sort=sort
                    )
                    return json.dumps(results, default=str)

                elif operation == "aggregate":
                    pipeline_str = args.get("pipeline", "[]")
                    pipeline = json.loads(pipeline_str)
                    results = await self.db.aggregate(collection, pipeline)
                    return json.dumps(results, default=str)

                elif operation == "count":
                    query = json.loads(args.get("query", "{}"))
                    # Use find and count since we don't have count_documents
                    results = await self.db.find(collection, query, limit=10000)
                    return json.dumps({"count": len(results)})

                else:
                    return json.dumps({"error": f"Unknown operation: {operation}"})

            except json.JSONDecodeError as e:
                return json.dumps({"error": f"Invalid JSON in query/pipeline: {str(e)}"})
            except Exception as e:
                logger.error(f"Database query failed: {e}")
                return json.dumps({"error": f"Database error: {str(e)}"})

        return json.dumps({"error": f"Unknown tool: {name}"})

    # ------------------------------------------------------------------
    # Main Orchestrator
    # ------------------------------------------------------------------
    async def process_message(
        self, session_id: str, user_message: str
    ) -> tuple[str, dict]:
        """
        Process a user message through the full conversational pipeline:
          1. Load history
          2. Build prompt with schema + context
          3. Call Gemini with function declarations
          4. If function_call → execute → feed result back → get final response
          5. Save turns
          6. Return (reply_text, metadata)
        """
        t0 = time.time()
        metadata = {"model": self.model, "tools_called": []}

        # 1. Load conversation history
        history = await self.load_history(session_id)

        # 2. Build the contents array for Gemini
        now = datetime.now(timezone.utc)
        system_prompt = SYSTEM_PROMPT.format(
            schema=SCHEMA_DESCRIPTION,
            current_date=now.strftime("%Y-%m-%d (%A)"),
        )

        # Convert history into Gemini content format
        contents = []
        for turn in history:
            role = "user" if turn["role"] == "user" else "model"
            contents.append(
                genai_types.Content(
                    role=role,
                    parts=[genai_types.Part.from_text(text=turn["content"])],
                )
            )

        # Add the new user message
        contents.append(
            genai_types.Content(
                role="user",
                parts=[genai_types.Part.from_text(text=user_message)],
            )
        )

        # 3. Call Gemini with tools
        config = genai_types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=[CHAT_TOOLS],
            temperature=0.3,
            top_p=0.9,
        )

        response = await call_gemini_with_retry(lambda: self.gemini.aio.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        ))

        # 4. Handle function calls (may require multiple rounds)
        max_rounds = 5
        round_count = 0

        while round_count < max_rounds:
            round_count += 1

            # Check if response contains a function call
            candidate = response.candidates[0] if response.candidates else None
            if not candidate or not candidate.content or not candidate.content.parts:
                break

            function_calls = [
                p for p in candidate.content.parts if p.function_call
            ]

            if not function_calls:
                # No more function calls — we have the final text response
                break

            # Execute each function call
            # Add Gemini's response (with function calls) to contents
            contents.append(candidate.content)

            for fc_part in function_calls:
                fc = fc_part.function_call
                logger.info(f"Executing tool: {fc.name}({json.dumps(dict(fc.args or {}), default=str)[:200]})")

                result_str = await self._execute_tool_call(fc)
                metadata["tools_called"].append({
                    "name": fc.name,
                    "args": dict(fc.args or {}),
                    "result_preview": result_str[:500],
                })

                # Add function response to contents
                contents.append(
                    genai_types.Content(
                        role="user",
                        parts=[
                            genai_types.Part.from_function_response(
                                name=fc.name,
                                response={"result": result_str},
                            )
                        ],
                    )
                )

            # Call Gemini again with the function results
            response = await call_gemini_with_retry(lambda: self.gemini.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            ))

        # 5. Extract final text response
        reply = ""
        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if part.text:
                    reply += part.text

        if not reply:
            reply = "I'm sorry, I couldn't process that request. Please try again."

        # 6. Extract choice block if any
        reply, choice = extract_and_validate_choice(reply)
        if choice:
            metadata["choice"] = choice

        # 7. Record latency
        metadata["latency_ms"] = int((time.time() - t0) * 1000)

        # 8. Save conversation turns (concurrently)
        import asyncio
        await asyncio.gather(
            self.save_turn(session_id, "user", user_message),
            self.save_turn(session_id, "assistant", reply, metadata),
        )

        return reply, metadata
