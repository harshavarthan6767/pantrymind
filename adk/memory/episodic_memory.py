import os
import json
from datetime import datetime
import google.generativeai as genai
from services.llm_client import call_gemini_sync_with_retry
from adk.memory.vector_memory import embed_text, embed_query

SUMMARY_EXTRACTION_PROMPT = """
Analyze this conversation and extract structured information.
Return ONLY JSON with no preamble:
{
  "summary":      "2-3 sentences describing what was accomplished",
  "key_facts":    ["fact about user preference/situation — max 5"],
  "session_type": "pantry|kitchen|finance|receipt|shopping|mixed"
}

Focus key_facts on: dietary restrictions, disliked ingredients, calorie targets,
cuisine preferences, budget constraints, household size, anything user explicitly stated.
"""


async def summarize_and_store_session(
    user_id: str,
    session_id: str,
    conversation_history: list
) -> None:
    """
    Called at session end via a FastAPI BackgroundTask.
    Summarizes the conversation and stores with embedding for future recall.
    """
    if len(conversation_history) < 3:
        return

    convo_text = "\n".join([
        f"{m['role'].upper()}: {m['content']}"
        for m in conversation_history[-24:]
    ])

    # Use cheapest model for summarization
    model = genai.GenerativeModel(
        model_name=os.getenv("FINANCE_MODEL", "gemini-3.1-flash-lite"),
        generation_config=genai.GenerationConfig(
            temperature=0.1,
            response_mime_type="application/json"
        )
    )

    try:
        result    = call_gemini_sync_with_retry(lambda: model.generate_content(f"{SUMMARY_EXTRACTION_PROMPT}\n\nCONVERSATION:\n{convo_text}"))
        raw       = result.text.strip()
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:-1])
        extracted = json.loads(raw)
    except Exception:
        return

    summary   = extracted.get("summary", "")
    embedding = embed_text(summary)

    from services.db_service import get_db
    db = await get_db()

    await db.conversation_summaries.insert_one({
        "user_id":      user_id,
        "session_id":   session_id,
        "summary":      summary,
        "key_facts":    extracted.get("key_facts", []),
        "embedding":    embedding,
        "session_type": extracted.get("session_type", "mixed"),
        "created_at":   datetime.utcnow()
    })

    # Upsert learned facts into user_preferences
    for fact in extracted.get("key_facts", []):
        await db.user_preferences.update_one(
            {"user_id": user_id},
            {
                "$push": {
                    "learned_facts_history": {
                        "fact":       fact,
                        "session_id": session_id,
                        "date":       datetime.utcnow()
                    }
                },
                "$set": {"last_updated": datetime.utcnow()}
            },
            upsert=True
        )


async def retrieve_relevant_memories(
    user_id: str,
    current_query: str,
    limit: int = 3
) -> str:
    """
    Returns a formatted string of the most relevant past session summaries.
    Injected at the top of each message in run_agent_streaming().

    Only injects if best memory score > 0.65 (avoids irrelevant noise).
    """
    from services.db_service import get_db
    db = await get_db()

    query_vector = embed_query(current_query)

    pipeline = [
        {
            "$vectorSearch": {
                "index":         os.getenv("SUMMARY_VECTOR_INDEX_NAME", "conversation_summary_index"),
                "path":          "embedding",
                "queryVector":   query_vector,
                "numCandidates": 50,
                "limit":         limit,
                "filter":        {"user_id": {"$eq": user_id}}
            }
        },
        {
            "$project": {
                "summary":    1,
                "key_facts":  1,
                "created_at": 1,
                "score":      {"$meta": "vectorSearchScore"}
            }
        }
    ]

    memories = await db.conversation_summaries.aggregate(pipeline).to_list(limit)

    # Filter low-relevance
    relevant = [m for m in memories if m.get("score", 0) >= 0.65]
    if not relevant:
        return ""

    lines = ["## RELEVANT PAST CONTEXT (from earlier sessions):"]
    for mem in relevant:
        date_str = mem["created_at"].strftime("%d %b") if "created_at" in mem else ""
        lines.append(f"[{date_str}] {mem['summary']}")
        for fact in mem.get("key_facts", [])[:3]:
            lines.append(f"  • {fact}")

    return "\n".join(lines)
