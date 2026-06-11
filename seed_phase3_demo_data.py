#!/usr/bin/env python
"""
seed_phase3_demo_data.py — Phase 3 · Day 3
===========================================
Seeds the MongoDB Atlas database with realistic demo data for hackathon judging.
Run this ONCE before the demo or before running evaluations.

Usage:
    .venv\\Scripts\\python seed_phase3_demo_data.py
    .venv\\Scripts\\python seed_phase3_demo_data.py --clear  # Wipe first then seed
"""
import asyncio
import datetime
import os
import sys
import argparse

import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

NOW = datetime.datetime.utcnow()

def days_ago(n: int) -> str:
    return (NOW - datetime.timedelta(days=n)).isoformat()

def days_from_now(n: int) -> str:
    return (NOW + datetime.timedelta(days=n)).isoformat()


INVENTORY = [
    # Expiring soon — should appear in meal plans
    {"name": "Salmon Fillet", "normalized_name": "salmon", "category": "MEAT_SEAFOOD",
     "sub_category": "seafood_fish", "dietary_flag": "SEAFOOD", "quantity": 0.5, "unit": "kg",
     "status": "Expiring Soon", "purchase_date": days_ago(4), "expiry_date": days_from_now(1),
     "safe_expiry_date": days_from_now(1), "is_consumed": False, "cost_per_unit": 320,
     "store": "Reliance Fresh", "is_perishable": True, "source": "demo_seed"},

    {"name": "Baby Spinach", "normalized_name": "spinach", "category": "PRODUCE",
     "sub_category": "leafy_greens", "dietary_flag": "VEGAN", "quantity": 200, "unit": "g",
     "status": "Expiring Soon", "purchase_date": days_ago(5), "expiry_date": days_from_now(2),
     "safe_expiry_date": days_from_now(1), "is_consumed": False, "cost_per_unit": 40,
     "store": "BigBasket", "is_perishable": True, "source": "demo_seed"},

    # Fresh items with Thai curry relevance (for semantic search scenario)
    {"name": "Coconut Milk", "normalized_name": "coconut milk", "category": "PANTRY_DRY",
     "sub_category": "canned_goods", "dietary_flag": "VEGAN", "quantity": 2, "unit": "cans",
     "status": "Fresh", "purchase_date": days_ago(10), "expiry_date": days_from_now(180),
     "safe_expiry_date": days_from_now(150), "is_consumed": False, "cost_per_unit": 55,
     "store": "DMart", "is_perishable": False, "source": "demo_seed"},

    {"name": "Thai Green Curry Paste", "normalized_name": "green curry paste", "category": "CONDIMENTS",
     "sub_category": "sauces", "dietary_flag": "VEGAN", "quantity": 1, "unit": "jar",
     "status": "Fresh", "purchase_date": days_ago(30), "expiry_date": days_from_now(60),
     "safe_expiry_date": days_from_now(45), "is_consumed": False, "cost_per_unit": 120,
     "store": "Amazon", "is_perishable": False, "source": "demo_seed"},

    {"name": "Jasmine Rice", "normalized_name": "jasmine rice", "category": "PANTRY_DRY",
     "sub_category": "rice_pasta", "dietary_flag": "VEGAN", "quantity": 1.5, "unit": "kg",
     "status": "Fresh", "purchase_date": days_ago(15), "expiry_date": days_from_now(300),
     "safe_expiry_date": days_from_now(270), "is_consumed": False, "cost_per_unit": 90,
     "store": "DMart", "is_perishable": False, "source": "demo_seed"},

    # Staples for shopping list
    {"name": "Free Range Eggs", "normalized_name": "eggs", "category": "DAIRY_EGGS",
     "sub_category": "eggs", "dietary_flag": "EGG", "quantity": 4, "unit": "piece",
     "status": "Fresh", "purchase_date": days_ago(3), "expiry_date": days_from_now(25),
     "safe_expiry_date": days_from_now(20), "is_consumed": False, "cost_per_unit": 8,
     "store": "Reliance Fresh", "is_perishable": True, "source": "demo_seed"},

    {"name": "Full Fat Milk", "normalized_name": "milk", "category": "DAIRY_EGGS",
     "sub_category": "milk", "dietary_flag": "DAIRY", "quantity": 0.5, "unit": "litre",
     "status": "Expiring Soon", "purchase_date": days_ago(6), "expiry_date": days_from_now(1),
     "safe_expiry_date": days_from_now(1), "is_consumed": False, "cost_per_unit": 30,
     "store": "Local Dairy", "is_perishable": True, "source": "demo_seed"},

    # Depleted items (should trigger shopping list)
    {"name": "Olive Oil", "normalized_name": "olive oil", "category": "PANTRY_DRY",
     "sub_category": "oil", "dietary_flag": "VEGAN", "quantity": 0.1, "unit": "litre",
     "status": "Critical", "purchase_date": days_ago(60), "expiry_date": days_from_now(300),
     "safe_expiry_date": days_from_now(250), "is_consumed": False, "cost_per_unit": 400,
     "store": "DMart", "is_perishable": False, "source": "demo_seed"},
]


FINANCIAL_LEDGER = [
    {"date": days_ago(2), "amount": 1240.50, "category": "groceries",
     "description": "Reliance Fresh — weekly groceries", "type": "expense"},
    {"date": days_ago(9), "amount": 3200.00, "category": "groceries",
     "description": "BigBasket online order", "type": "expense"},
    {"date": days_ago(14), "amount": 850.00, "category": "dining_out",
     "description": "Restaurant — family dinner", "type": "expense"},
    {"date": days_ago(20), "amount": 560.00, "category": "groceries",
     "description": "Local kirana — vegetables", "type": "expense"},
    {"date": days_ago(1), "amount": 45000.00, "category": "salary",
     "description": "Monthly salary credit", "type": "income"},
]

USER_PROFILE = {
    "user_id": "default_user",
    "name": "Harsh",
    "monthly_food_budget": 8000.0,
    "dietary_preference": "VEG",
    "calorie_target": 2200,
    "household_size": 2,
    "preferred_cuisine": ["Indian", "Thai", "Mediterranean"],
    "created_at": days_ago(30)
}


async def seed(db, clear: bool):
    if clear:
        print("🗑️  Clearing existing demo data...")
        await db["inventory"].delete_many({"source": "demo_seed"})
        await db["financial_ledger"].delete_many({})
        await db["user_profile"].delete_many({"user_id": "default_user"})
        print("   Done.")

    # Inventory
    print("🌿 Seeding inventory...")
    result = await db["inventory"].insert_many(INVENTORY)
    print(f"   ✓ {len(result.inserted_ids)} inventory items inserted")

    # Financial ledger
    print("💰 Seeding financial ledger...")
    result = await db["financial_ledger"].insert_many(FINANCIAL_LEDGER)
    print(f"   ✓ {len(result.inserted_ids)} transactions inserted")

    # User profile
    print("👤 Seeding user profile...")
    await db["user_profile"].update_one(
        {"user_id": "default_user"},
        {"$set": USER_PROFILE},
        upsert=True
    )
    print("   ✓ User profile upserted")

    print("\n✅ Demo data seeded successfully!")
    print("   Ready to run: .venv\\Scripts\\python run_phase3_evals.py")


async def main(clear: bool):
    uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGODB_DATABASE", "finmind")
    if not uri:
        print("❌ MONGODB_URI not set"); sys.exit(1)

    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=10000, tlsCAFile=certifi.where())
    db = client[db_name]
    await seed(db, clear)
    client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--clear", action="store_true", help="Clear existing demo data first")
    args = parser.parse_args()
    asyncio.run(main(clear=args.clear))
