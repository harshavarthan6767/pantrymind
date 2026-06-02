#!/usr/bin/env python3
"""MongoDB Atlas setup script for PantryMind.

Creates collections, indexes, vector search definition,
default user profile, and sample data.

Usage:
    python scripts/setup_mongodb.py
"""

import asyncio
import os
from datetime import datetime

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING, TEXT, IndexModel

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = "pantrymind"

COLLECTIONS = [
    "inventory",
    "receipts",
    "consumption_history",
    "financial_ledger",
    "warranties",
    "user_profile",
    "behavior_snapshots",
    "carbon_log",
    "nutrition_log",
    "restock_predictions",
]

INDEX_DEFINITIONS: dict[str, list[IndexModel]] = {
    "inventory": [
        IndexModel([("item_name", TEXT)], name="idx_inventory_item_name_text"),
        IndexModel(
            [("category", ASCENDING), ("purchase_date", ASCENDING)],
            name="idx_inventory_category_purchase",
        ),
    ],
    "receipts": [
        IndexModel([("date", DESCENDING)], name="idx_receipts_date_desc"),
    ],
    "consumption_history": [
        IndexModel(
            [("month_key", ASCENDING), ("item_name", ASCENDING)],
            name="idx_consumption_month_item",
        ),
    ],
    "financial_ledger": [
        IndexModel([("date", DESCENDING)], name="idx_ledger_date_desc"),
    ],
    "warranties": [
        IndexModel([("expiry_date", ASCENDING)], name="idx_warranties_expiry_asc"),
    ],
    "user_profile": [
        IndexModel([("user_id", ASCENDING)], name="idx_user_id_unique", unique=True),
    ],
    "behavior_snapshots": [
        IndexModel([("week_key", DESCENDING)], name="idx_behavior_week_desc"),
    ],
    "carbon_log": [
        IndexModel([("date", DESCENDING)], name="idx_carbon_date_desc"),
    ],
    "nutrition_log": [
        IndexModel([("date", DESCENDING)], name="idx_nutrition_date_desc"),
    ],
    "restock_predictions": [
        IndexModel(
            [("predicted_empty_date", ASCENDING)],
            name="idx_restock_predicted_empty_asc",
        ),
    ],
}

DEFAULT_USER_PROFILE = {
    "user_id": "default_user",
    "name": "PantryMind User",
    "monthly_salary": 0,
    "tax_regime": "new",
    "dietary_preferences": [],
    "allergies": [],
    "household_size": 1,
    "created_at": datetime.utcnow(),
}

SAMPLE_INVENTORY = [
    {
        "item_name": "Basmati Rice",
        "category": "grains",
        "quantity": 5000,
        "unit": "g",
        "purchase_date": datetime(2026, 5, 25),
        "expiry_date": datetime(2027, 5, 25),
        "price": 450.0,
        "added_at": datetime.utcnow(),
    },
    {
        "item_name": "Toor Dal",
        "category": "pulses",
        "quantity": 1000,
        "unit": "g",
        "purchase_date": datetime(2026, 5, 20),
        "expiry_date": datetime(2027, 2, 20),
        "price": 180.0,
        "added_at": datetime.utcnow(),
    },
    {
        "item_name": "Amul Butter",
        "category": "dairy",
        "quantity": 500,
        "unit": "g",
        "purchase_date": datetime(2026, 5, 28),
        "expiry_date": datetime(2026, 8, 28),
        "price": 280.0,
        "added_at": datetime.utcnow(),
    },
    {
        "item_name": "Onions",
        "category": "vegetables",
        "quantity": 2000,
        "unit": "g",
        "purchase_date": datetime(2026, 5, 30),
        "expiry_date": None,
        "price": 60.0,
        "added_at": datetime.utcnow(),
    },
    {
        "item_name": "Tomatoes",
        "category": "vegetables",
        "quantity": 1000,
        "unit": "g",
        "purchase_date": datetime(2026, 5, 31),
        "expiry_date": None,
        "price": 40.0,
        "added_at": datetime.utcnow(),
    },
    {
        "item_name": "Chicken Breast",
        "category": "meat",
        "quantity": 1000,
        "unit": "g",
        "purchase_date": datetime(2026, 6, 1),
        "expiry_date": datetime(2026, 6, 4),
        "price": 320.0,
        "added_at": datetime.utcnow(),
    },
    {
        "item_name": "Milk",
        "category": "dairy",
        "quantity": 1000,
        "unit": "ml",
        "purchase_date": datetime(2026, 6, 1),
        "expiry_date": datetime(2026, 6, 4),
        "price": 68.0,
        "added_at": datetime.utcnow(),
    },
    {
        "item_name": "Eggs",
        "category": "dairy",
        "quantity": 12,
        "unit": "pcs",
        "purchase_date": datetime(2026, 5, 29),
        "expiry_date": datetime(2026, 6, 12),
        "price": 96.0,
        "added_at": datetime.utcnow(),
    },
]

VECTOR_SEARCH_INDEX_DEFINITION = {
    "name": "vector_index",
    "type": "vectorSearch",
    "definition": {
        "fields": [
            {
                "type": "vector",
                "path": "embedding",
                "numDimensions": 768,
                "similarity": "cosine",
            }
        ]
    },
}


async def create_collections(db):
    """Create all required collections."""
    existing = await db.list_collection_names()
    for coll_name in COLLECTIONS:
        if coll_name not in existing:
            await db.create_collection(coll_name)
            print(f"  ✅ Created collection: {coll_name}")
        else:
            print(f"  ⏭️  Collection already exists: {coll_name}")


async def create_indexes(db):
    """Create all indexes on collections."""
    for coll_name, indexes in INDEX_DEFINITIONS.items():
        coll = db[coll_name]
        for idx in indexes:
            try:
                await coll.create_indexes([idx])
                idx_name = idx.document.get("name", "unnamed")
                print(f"  ✅ Index '{idx_name}' on '{coll_name}'")
            except Exception as e:
                print(f"  ⚠️  Index error on '{coll_name}': {e}")


async def insert_default_user(db):
    """Insert default user profile if not present."""
    coll = db["user_profile"]
    existing = await coll.find_one({"user_id": "default_user"})
    if existing:
        print("  ⏭️  Default user profile already exists")
    else:
        await coll.insert_one(DEFAULT_USER_PROFILE)
        print("  ✅ Inserted default user profile")


async def seed_sample_inventory(db):
    """Seed sample inventory items."""
    coll = db["inventory"]
    count = await coll.count_documents({})
    if count > 0:
        print(f"  ⏭️  Inventory already has {count} items, skipping seed")
    else:
        result = await coll.insert_many(SAMPLE_INVENTORY)
        print(f"  ✅ Seeded {len(result.inserted_ids)} sample inventory items")


def print_vector_search_index():
    """Print Atlas Vector Search index definition for manual creation."""
    import json

    print("\n" + "=" * 60)
    print("ATLAS VECTOR SEARCH INDEX")
    print("=" * 60)
    print(
        "Create this index manually via the Atlas UI on the 'inventory' collection:"
    )
    print(json.dumps(VECTOR_SEARCH_INDEX_DEFINITION, indent=2))
    print("=" * 60 + "\n")


async def main():
    """Run the full MongoDB setup."""
    print(f"\n🚀 PantryMind MongoDB Setup")
    print(f"   URI: {MONGODB_URI[:30]}...")
    print(f"   Database: {DB_NAME}\n")

    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DB_NAME]

    # Verify connectivity
    try:
        await client.admin.command("ping")
        print("✅ Connected to MongoDB\n")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    print("📦 Creating collections...")
    await create_collections(db)

    print("\n📇 Creating indexes...")
    await create_indexes(db)

    print("\n👤 Setting up default user profile...")
    await insert_default_user(db)

    print("\n🥫 Seeding sample inventory...")
    await seed_sample_inventory(db)

    print_vector_search_index()

    print("✅ Setup complete!\n")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
