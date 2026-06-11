"""
PantryMind Finance Chat Service — Gemini 3.1 Flash Lite Agent

Handles structured financial queries (ledger lookups, budget math, expense
tallies, category breakdowns) using a cheaper model. Uses the same
google.genai SDK + function-calling pattern as the main ChatService.
"""

import os
import json
import logging
import time
from datetime import datetime, timezone, timedelta

from google.genai import types as genai_types
from services.llm_client import call_gemini_with_retry
from services.chat_service import extract_and_validate_choice
from dateutil.relativedelta import relativedelta

logger = logging.getLogger("pantrymind.finance")

# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------
FINANCE_SYSTEM_PROMPT = """You are the PantryMind Finance Agent — a household budget and expense analyst.

## YOUR ROLE
Analyze the user's spending data, provide summaries, compute budgets, and give
financial insights based solely on their receipt and ledger data.

## WHAT YOU DO
- Query the financial ledger for expenses by date range and category
- Calculate total spending, category breakdowns, and month-over-month changes
- Compare actual spend against declared salary and budget targets
- Calculate disposable income after tracked expenses
- Identify the biggest expense categories and flag overspending
- Answer questions like: "How much did I spend on groceries last month?",
  "What's my biggest expense category?", "How does this week compare to last week?"

## TOOL USAGE — MANDATORY
You MUST call tools to get real data. Never estimate or invent numbers.
Always call the appropriate tool first, then compute, then reply.

## RESPONSE STYLE
- Lead with the direct number answer (e.g., "You spent ₹4,230 on groceries in May.")
- Follow with a one-line comparison or insight.
- Keep responses short — 2-4 sentences unless the user asks for a breakdown.
- Use ₹ for currency (INR default). Adapt if user's data shows otherwise.
- Round all rupee amounts to the nearest integer.
- Never ask for clarification on date ranges — default to current month if unspecified.
- Today's date is {current_date}.
"""

# ---------------------------------------------------------------------------
# Tool Declarations
# ---------------------------------------------------------------------------
QUERY_LEDGER_TOOL = genai_types.FunctionDeclaration(
    name="query_ledger",
    description=(
        "Get expense data from the financial ledger by date range and optional category. "
        "Returns aggregated totals by category. Call this first for any spending question."
    ),
    parameters=genai_types.Schema(
        type="OBJECT",
        properties={
            "start_date": genai_types.Schema(
                type="STRING",
                description="Start date — ISO format or shorthand: 'this month', 'last month', 'last 30 days', 'last 7 days'",
            ),
            "end_date": genai_types.Schema(
                type="STRING",
                description="End date in ISO format. Optional — defaults to now.",
            ),
            "category": genai_types.Schema(
                type="STRING",
                description="Filter by category, e.g. 'groceries', 'household', 'personal_care'. Optional.",
            ),
        },
    ),
)

GET_BUDGET_SUMMARY_TOOL = genai_types.FunctionDeclaration(
    name="get_budget_summary",
    description="Get salary, monthly spend so far, disposable income remaining, and spend rate percentage.",
    parameters=genai_types.Schema(
        type="OBJECT",
        properties={},
    ),
)

COMPARE_MONTHS_TOOL = genai_types.FunctionDeclaration(
    name="compare_months",
    description="Compare this month's spending to a previous month. Returns totals for both months and the change.",
    parameters=genai_types.Schema(
        type="OBJECT",
        properties={
            "months_back": genai_types.Schema(
                type="INTEGER",
                description="How many months back to compare (default 1 = last month).",
            ),
        },
    ),
)

FINANCE_TOOLS = genai_types.Tool(
    function_declarations=[QUERY_LEDGER_TOOL, GET_BUDGET_SUMMARY_TOOL, COMPARE_MONTHS_TOOL]
)


# ---------------------------------------------------------------------------
# Date Parsing Utility
# ---------------------------------------------------------------------------
def _parse_date_range(start_date: str | None, end_date: str | None):
    """Parse natural language or ISO date strings into datetime objects."""
    now = datetime.now(timezone.utc)
    if not start_date or start_date == "this month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif start_date == "last month":
        start = (now.replace(day=1) - relativedelta(months=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(seconds=1)
    elif start_date == "last 30 days":
        start = now - timedelta(days=30)
        end = now
    elif start_date == "last 7 days":
        start = now - timedelta(days=7)
        end = now
    else:
        try:
            start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        except Exception:
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        try:
            end = datetime.fromisoformat(end_date.replace("Z", "+00:00")) if end_date else now
        except Exception:
            end = now
    return start, end


# ---------------------------------------------------------------------------
# Finance Chat Service
# ---------------------------------------------------------------------------
class FinanceChatService:
    """
    Orchestrates finance-specific conversations using Gemini Flash Lite
    with custom tools for ledger queries, budget summaries, and comparisons.
    """

    def __init__(self, db_service, gemini_client, model_name: str = None):
        self.db = db_service
        self.gemini = gemini_client
        self.model = model_name or "gemini-3.1-flash-lite"

    # ------------------------------------------------------------------
    # Tool Execution
    # ------------------------------------------------------------------
    async def _execute_tool_call(self, function_call, user_id: str) -> str:
        """Execute a finance function call and return JSON result."""
        name = function_call.name
        args = dict(function_call.args or {})

        if name == "query_ledger":
            return await self._query_ledger(
                start_date=args.get("start_date"),
                end_date=args.get("end_date"),
                category=args.get("category"),
                user_id=user_id,
            )

        if name == "get_budget_summary":
            return await self._get_budget_summary(user_id)

        if name == "compare_months":
            return await self._compare_months(int(args.get("months_back", 1)), user_id)

        return json.dumps({"error": f"Unknown tool: {name}"})

    async def _query_ledger(
        self, start_date: str = None, end_date: str = None, category: str = None, user_id: str = None
    ) -> str:
        """Aggregate financial_ledger entries by category in a date range."""
        start, end = _parse_date_range(start_date, end_date)

        match_stage: dict = {
            "type": "expense",
            "date": {"$gte": start.isoformat(), "$lte": end.isoformat()},
            "user_id": user_id,
        }
        if category:
            match_stage["category"] = {"$regex": category, "$options": "i"}

        pipeline = [
            {"$match": match_stage},
            {
                "$group": {
                    "_id": "$category",
                    "total": {"$sum": "$amount"},
                    "count": {"$sum": 1},
                    "latest_date": {"$max": "$date"},
                }
            },
            {"$sort": {"total": -1}},
        ]

        results = await self.db.aggregate("financial_ledger", pipeline)
        grand_total = sum(r.get("total", 0) for r in results)

        output = {
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "grand_total": round(grand_total, 2),
            "by_category": [
                {
                    "category": r["_id"],
                    "total": round(r["total"], 2),
                    "pct_of_spend": round(
                        (r["total"] / grand_total * 100) if grand_total else 0, 1
                    ),
                    "num_transactions": r["count"],
                }
                for r in results
            ],
            "num_transactions": sum(r.get("count", 0) for r in results),
        }
        return json.dumps(output, default=str)

    async def _get_budget_summary(self, user_id: str = None) -> str:
        """Return salary, current-month spend, and disposable income."""
        profile = await self.db.find_one("user_profile", {}) # Profile doesn't have user_id yet
        monthly_salary = profile.get("monthly_salary", 0) if profile else 0

        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        pipeline = [
            {
                "$match": {
                    "type": "expense",
                    "date": {"$gte": month_start.isoformat()},
                    "user_id": user_id,
                }
            },
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
        ]
        agg = await self.db.aggregate("financial_ledger", pipeline)
        spent = agg[0]["total"] if agg else 0

        disposable = monthly_salary - spent
        next_month = month_start + relativedelta(months=1)
        days_left = (next_month - now).days

        output = {
            "monthly_salary": round(monthly_salary, 2),
            "spent_this_month": round(spent, 2),
            "disposable_income": round(disposable, 2),
            "spend_rate_pct": round(
                (spent / monthly_salary * 100) if monthly_salary else 0, 1
            ),
            "days_left_in_month": days_left,
        }
        return json.dumps(output, default=str)

    async def _compare_months(self, months_back: int = 1, user_id: str = None) -> str:
        """Compare current month spend to a previous month."""
        now = datetime.now(timezone.utc)
        this_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        prev_start = this_start - relativedelta(months=months_back)
        prev_end = this_start - timedelta(seconds=1)

        async def _total_in_range(start_iso: str, end_iso: str) -> float:
            pipeline = [
                {
                    "$match": {
                        "type": "expense",
                        "date": {"$gte": start_iso, "$lte": end_iso},
                        "user_id": user_id,
                    }
                },
                {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
            ]
            agg = await self.db.aggregate("financial_ledger", pipeline)
            return agg[0]["total"] if agg else 0

        this_total = await _total_in_range(this_start.isoformat(), now.isoformat())
        prev_total = await _total_in_range(prev_start.isoformat(), prev_end.isoformat())

        delta = this_total - prev_total
        delta_pct = (delta / prev_total * 100) if prev_total else 0

        output = {
            "this_month": {
                "total": round(this_total, 2),
                "period": this_start.strftime("%B %Y"),
            },
            "previous_month": {
                "total": round(prev_total, 2),
                "period": prev_start.strftime("%B %Y"),
            },
            "change_amount": round(delta, 2),
            "change_pct": round(delta_pct, 1),
            "trend": "up" if delta > 0 else ("down" if delta < 0 else "flat"),
        }
        return json.dumps(output, default=str)

    # ------------------------------------------------------------------
    # Main Orchestrator
    # ------------------------------------------------------------------
    async def process_message(
        self, session_id: str, user_message: str, user_id: str
    ) -> tuple[str, dict]:
        """
        Full pipeline: system prompt → Gemini w/ finance tools → tool loop → answer.
        """
        t0 = time.time()
        metadata = {"model": self.model, "tools_called": []}

        now = datetime.now(timezone.utc)
        system_prompt = FINANCE_SYSTEM_PROMPT.format(
            current_date=now.strftime("%Y-%m-%d (%A)")
        )

        # Load conversation history for this session
        history = await self.db.find(
            "finance_conversation_history",
            {"session_id": session_id},
            limit=20,
            sort=[("timestamp", 1)],
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

        contents.append(
            genai_types.Content(
                role="user",
                parts=[genai_types.Part.from_text(text=user_message)],
            )
        )

        config = genai_types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=[FINANCE_TOOLS],
            temperature=0.2,
            top_p=0.9,
        )

        response = await call_gemini_with_retry(lambda: self.gemini.aio.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        ))

        # Tool-call loop (max 5 rounds)
        max_rounds = 5
        for _ in range(max_rounds):
            candidate = response.candidates[0] if response.candidates else None
            if not candidate or not candidate.content or not candidate.content.parts:
                break

            function_calls = [p for p in candidate.content.parts if p.function_call]
            if not function_calls:
                break

            contents.append(candidate.content)

            for fc_part in function_calls:
                fc = fc_part.function_call
                logger.info(f"Finance tool: {fc.name}({json.dumps(dict(fc.args or {}), default=str)[:200]})")

                result_str = await self._execute_tool_call(fc, user_id)
                metadata["tools_called"].append({
                    "name": fc.name,
                    "args": dict(fc.args or {}),
                    "result_preview": result_str[:500],
                })

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

            response = await call_gemini_with_retry(lambda: self.gemini.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            ))

        # Extract final text
        reply = ""
        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if part.text:
                    reply += part.text

        if not reply:
            reply = "I couldn't process that finance query. Please try rephrasing."

        # Extract choice block if any
        reply, choice = extract_and_validate_choice(reply)
        if choice:
            metadata["choice"] = choice

        metadata["latency_ms"] = int((time.time() - t0) * 1000)

        # Save conversation history
        import asyncio
        await asyncio.gather(
            self.db.insert_one("finance_conversation_history", {
                "session_id": session_id,
                "role": "user",
                "content": user_message,
                "timestamp": now.isoformat(),
            }),
            self.db.insert_one("finance_conversation_history", {
                "session_id": session_id,
                "role": "assistant",
                "content": reply,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }),
        )

        return reply, metadata
