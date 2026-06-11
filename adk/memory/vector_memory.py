import os
import re
from typing import Optional
import vertexai
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput
from pymongo.errors import OperationFailure

vertexai.init(
    project=os.getenv("GOOGLE_CLOUD_PROJECT"),
    location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
)
_model = None

def _get_model():
    global _model
    if _model is None:
        _model = TextEmbeddingModel.from_pretrained(
            os.getenv("EMBEDDING_MODEL", "text-embedding-004")
        )
    return _model


def build_inventory_document_text(item: dict) -> str:
    """
    Converts an inventory item to a rich text blob for embedding.
    The richer this text, the better semantic search works.

    Example output:
    "chicken breast | category: meat seafood | subcategory: poultry |
     diet: NON_VEG | status: Fresh | store in fridge 0-4°C |
     protein grilling stir-fry curry roasting"
    """
    name     = item.get("normalized_name") or item.get("name", "")
    category = item.get("category", "").replace("_", " ").lower()
    sub_cat  = item.get("sub_category", "").replace("_", " ").lower()
    diet     = item.get("dietary_flag", "NA")
    status   = item.get("status", "")
    storage  = item.get("storage_note", "")

    USE_TAGS = {
        "MEAT_SEAFOOD":  "protein grilling stir-fry curry roasting non-veg",
        "PRODUCE":       "salad stir-fry soup smoothie fresh vegetables fruit",
        "DAIRY_EGGS":    "baking breakfast omelette dessert sauce dairy protein",
        "PANTRY_DRY":    "staple base grain rice dal flour oil spice pantry",
        "BEVERAGES":     "drink juice tea coffee morning breakfast hydration",
        "CONDIMENTS":    "flavoring sauce marinade seasoning ketchup chutney",
        "FROZEN":        "quick meal convenience frozen ready-to-cook",
        "BAKERY":        "breakfast snack bread bun roti toast",
        "SNACKS":        "snack quick bite chips biscuit energy bar",
    }
    use_tags = USE_TAGS.get(item.get("category", ""), "")

    return (
        f"{name} | category: {category} | subcategory: {sub_cat} | "
        f"diet: {diet} | status: {status} | {storage} | {use_tags}"
    ).strip(" |")


def embed_text(text: str) -> list[float]:
    """768-dim embedding for a document (indexing time)."""
    inputs = [TextEmbeddingInput(text=text, task_type="RETRIEVAL_DOCUMENT")]
    return _get_model().get_embeddings(inputs)[0].values


def embed_query(query: str) -> list[float]:
    """768-dim embedding for a search query (query time)."""
    inputs = [TextEmbeddingInput(text=query, task_type="RETRIEVAL_QUERY")]
    return _get_model().get_embeddings(inputs)[0].values


async def semantic_pantry_search(
    query: str,
    limit: int = 10,
    only_unconsumed: bool = True,
    status_filter: Optional[list] = None,
    dietary_filter: Optional[str] = None,
    user_id: Optional[str] = None,
) -> list[dict]:
    """
    Performs Atlas Vector Search over inventory using a natural language query.

    Called by Pantry Agent and Kitchen Chef for open-ended ingredient queries:
      "ingredients for Thai curry"
      "quick protein that's expiring"
      "something for a smoothie"

    Returns items ranked by cosine similarity, each with a `score` field.
    Items with score > 0.75 are strongly relevant.
    Items with score < 0.60 should be ignored.

    status_filter example: ["Fresh", "Expiring Soon"]
    dietary_filter example: "VEG"
    """
    from services.db_service import get_db
    db = await get_db()

    query_vector = embed_query(query)

    effective_user_id = user_id or os.getenv("DEMO_USER_ID", "demo_user_001")
    pre_filter = {"user_id": {"$eq": effective_user_id}}
    if only_unconsumed:
        pre_filter["is_consumed"] = {"$eq": False}
    if status_filter:
        pre_filter["status"] = {"$in": status_filter}
    if dietary_filter:
        # Map dietary preference to acceptable dietary_flags
        ACCEPTABLE_FLAGS = {
            "VEG":   ["VEG", "VEGAN", "DAIRY", "EGG", "NA"],
            "VEGAN": ["VEGAN", "NA"],
            "NON_VEG": ["VEG", "NON_VEG", "VEGAN", "DAIRY", "SEAFOOD", "EGG", "NA"],
        }
        flags = ACCEPTABLE_FLAGS.get(dietary_filter.upper())
        if flags:
            pre_filter["dietary_flag"] = {"$in": flags}

    pipeline = [
        {
            "$vectorSearch": {
                "index":         os.getenv("VECTOR_INDEX_NAME", "inventory_vector_index"),
                "path":          "embedding",
                "queryVector":   query_vector,
                "numCandidates": 150,
                "limit":         limit,
                "filter":        pre_filter
            }
        },
        {
            "$project": {
                "name":             1,
                "normalized_name":  1,
                "category":         1,
                "sub_category":     1,
                "dietary_flag":     1,
                "quantity":         1,
                "unit":             1,
                "status":           1,
                "expiry_date":      1,
                "safe_expiry_date": 1,
                "storage_note":     1,
                "score":            {"$meta": "vectorSearchScore"}
            }
        }
    ]

    try:
        results = await db.inventory.aggregate(pipeline).to_list(limit)
    except OperationFailure as exc:
        if "needs to be indexed as filter" not in str(exc):
            raise

        active_filter = {
            "user_id": effective_user_id,
            "is_consumed": {"$ne": True},
        }
        broad_inventory_query = any(
            phrase in query.lower()
            for phrase in (
                "list all",
                "list every",
                "my inventory",
                "what do i have",
                "what's in",
                "everything",
            )
        )

        if not broad_inventory_query:
            stop_words = {
                "anything", "find", "for", "from", "have", "ingredients",
                "inventory", "make", "my", "pantry", "quick", "show",
                "something", "that", "the", "what", "with",
            }
            terms = [
                re.escape(term)
                for term in re.findall(r"[a-zA-Z0-9]+", query.lower())
                if len(term) > 2 and term not in stop_words
            ]
            if terms:
                pattern = "|".join(terms)
                active_filter["$or"] = [
                    {"name": {"$regex": pattern, "$options": "i"}},
                    {"normalized_name": {"$regex": pattern, "$options": "i"}},
                    {"category": {"$regex": pattern, "$options": "i"}},
                    {"sub_category": {"$regex": pattern, "$options": "i"}},
                ]

        projection = {
            "name": 1,
            "normalized_name": 1,
            "category": 1,
            "sub_category": 1,
            "dietary_flag": 1,
            "quantity": 1,
            "unit": 1,
            "status": 1,
            "expiry_date": 1,
            "safe_expiry_date": 1,
            "storage_note": 1,
        }
        results = await db.inventory.find(
            active_filter,
            projection,
        ).limit(limit).to_list(limit)

    # Filter out low-confidence results
    return [
        r for r in results
        if "score" not in r or r.get("score", 0) >= 0.60
    ]
