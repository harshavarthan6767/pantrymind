# scripts/setup_vector_index.py
# Run: python scripts/setup_vector_index.py

from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

def create_vector_indexes():
    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client[os.getenv("MONGODB_DATABASE", "finmind")]

    # Create collections if they don't exist
    if "inventory" not in db.list_collection_names():
        db.create_collection("inventory")
    if "conversation_summaries" not in db.list_collection_names():
        db.create_collection("conversation_summaries")

    # ── Inventory vector index ──────────────────────────────────────────
    db.command({
        "createSearchIndexes": "inventory",
        "indexes": [
            {
                "name": "inventory_vector_index",
                "type": "vectorSearch",
                "definition": {
                    "fields": [
                        {
                            "type":          "vector",
                            "path":          "embedding",
                            "numDimensions": 768,
                            "similarity":    "cosine"
                        },
                        {"type": "filter", "path": "is_consumed"},
                        {"type": "filter", "path": "status"},
                        {"type": "filter", "path": "category"},
                        {"type": "filter", "path": "dietary_flag"}
                    ]
                }
            }
        ]
    })
    print("inventory_vector_index created")

    # ── Conversation summary index ───────────────────────────────────────
    db.command({
        "createSearchIndexes": "conversation_summaries",
        "indexes": [
            {
                "name": "conversation_summary_index",
                "type": "vectorSearch",
                "definition": {
                    "fields": [
                        {
                            "type":          "vector",
                            "path":          "embedding",
                            "numDimensions": 768,
                            "similarity":    "cosine"
                        },
                        {"type": "filter", "path": "user_id"},
                        {"type": "filter", "path": "session_type"}
                    ]
                }
            }
        ]
    })
    print("conversation_summary_index created")

if __name__ == "__main__":
    create_vector_indexes()
