import os
import json
import logging
import google.generativeai as genai
from typing import Optional
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from services.llm_client import call_gemini_sync_with_retry

CRITIQUE_PROMPT = """
You are a strict quality reviewer for an AI assistant response.

## ORIGINAL USER QUERY:
{user_query}

## DRAFT RESPONSE:
{draft_response}

## DOMAIN CHECKLIST:
{checklist}

Review the draft strictly against the checklist.
Return ONLY JSON with no preamble or markdown fences:
{{
  "passed": true/false,
  "issues": ["issue 1", "issue 2"],
  "severity": "none" | "minor" | "major",
  "revised_response": "full corrected response OR null"
}}

Severity rules:
  "none"  → no issues found: set passed=true, revised_response=null
  "minor" → style/completeness issues only: set passed=true, revised_response=null
  "major" → factual errors, wrong numbers, missing required fields, violated dietary rules:
             set passed=false, write full revised_response
"""

DOMAIN_CHECKLISTS = {
    "kitchen": """
- Are all ingredient quantities specific numbers with units (grams or ml)?
  NO: "some rice", "a handful of dal" — YES: "200g rice", "80g dal"
- Does the total kcal match the sum of macro kcals (protein*4 + carbs*4 + fat*9)?
  Allow ±10 kcal tolerance.
- Is there a nutrition summary line: Xkcal · Xg protein · Xg carbs · Xg fat?
- Are cooking temperature and time given for every heat step?
- Is the user's dietary preference respected?
  If VEG: zero NON_VEG or SEAFOOD items allowed.
- Are expiring items flagged with ⚠️ and their expiry date?
""",
    "finance": """
- Are all amounts in ₹ (INR)?
- Is the date range explicitly stated (e.g., "June 1–6, 2026")?
- Are all numbers sourced from actual DB query results, not estimated?
- Is the key figure the first thing stated, not buried?
- Is the response concise: 2–3 sentences max unless a breakdown was requested?
- If a percentage is stated, is it mathematically correct?
""",
    "pantry": """
- Are expiry dates given as "X days from today" not just ISO strings?
- Are quantities reported with units?
- Is the status value one of: Fresh, Expiring Soon, Critical, Expired, N/A?
- If items are expiring, is the exact day count stated?
- Are consumed items excluded from all counts?
""",
    "receipt": """
- Were all workflow steps confirmed: parse → expiry → insertMany → insertOne (ledger)?
- Is the item count explicitly stated?
- Is the total expense in ₹?
- Are any CGST/SGST/tax lines mentioned as products? (They must NOT be.)
- Is the success message unambiguous?
""",
    "shopping": """
- Is every item in Priority 1 genuinely essential (depleted, expiring, or meal-required)?
- Are estimated costs realistic for Indian grocery prices (2026)?
- Is the total within or clearly compared to remaining budget?
- Are items grouped by priority tier?
"""
}


def apply_reflexion(
    user_query: str,
    draft_response: str,
    domain: str,
    model_name: Optional[str] = None
) -> str:
    """
    Runs a critique pass on the agent's draft before it reaches the user.

    Returns:
      - Original draft if severity is "none" or "minor"
      - Revised response if severity is "major"
      - Original draft if critique call fails (fail-safe)

    Cost: ~200-400 tokens per critique call (gemini-3.1-flash-lite).
    Only the major-severity branch triggers the full revised response generation.
    """
    if not os.getenv("ENABLE_REFLEXION", "true").lower() == "true":
        return draft_response

    checklist  = DOMAIN_CHECKLISTS.get(domain, "")
    model_name = model_name or os.getenv("FINANCE_MODEL", "gemini-3.1-flash-lite")

    prompt = CRITIQUE_PROMPT.format(
        user_query=user_query,
        draft_response=draft_response,
        checklist=checklist
    )

    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config=genai.GenerationConfig(
            temperature=0.1,
            response_mime_type="application/json"
        )
    )

    try:
        result = call_gemini_sync_with_retry(lambda: model.generate_content(prompt))
        raw    = result.text.strip()
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:-1])
        critique = json.loads(raw)

        if not critique.get("passed") and critique.get("revised_response"):
            return critique["revised_response"]

        return draft_response

    except Exception:
        return draft_response   # Never break the main flow
