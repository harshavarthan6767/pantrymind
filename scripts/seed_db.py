"""
Seed PantryMind MongoDB with demo inventory, receipts, and profile data.
Run once: python scripts/seed_db.py
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from services.db_service import MongoDBService


async def seed():
    db = MongoDBService()
    await db.connect()

    # ── Clear existing demo data ──
    for col in ["inventory", "receipts", "consumption_history", "financial_ledger",
                 "warranties", "user_profile", "carbon_log", "nutrition_log"]:
        await db.db[col].delete_many({})

    now = datetime.utcnow()

    # ── Inventory (20 items) ──
    inventory = [
        {"name": "Basmati Rice", "category": "Grains", "quantity": 5, "unit": "kg",
         "purchase_date": (now - timedelta(days=18)).isoformat(),
         "expiry_date": (now + timedelta(days=165)).isoformat(), "status": "fresh",
         "cost_per_unit": 85, "store": "BigBasket"},
        {"name": "Toor Dal", "category": "Grains", "quantity": 2, "unit": "kg",
         "purchase_date": (now - timedelta(days=12)).isoformat(),
         "expiry_date": (now + timedelta(days=80)).isoformat(), "status": "fresh",
         "cost_per_unit": 120, "store": "DMart"},
        {"name": "Paneer", "category": "Dairy", "quantity": 500, "unit": "g",
         "purchase_date": (now - timedelta(days=4)).isoformat(),
         "expiry_date": (now + timedelta(days=1)).isoformat(), "status": "expiring",
         "cost_per_unit": 320, "store": "BigBasket"},
        {"name": "Tomatoes", "category": "Produce", "quantity": 1, "unit": "kg",
         "purchase_date": (now - timedelta(days=3)).isoformat(),
         "expiry_date": (now + timedelta(days=1)).isoformat(), "status": "expiring",
         "cost_per_unit": 40, "store": "Local Vendor"},
        {"name": "Milk", "category": "Dairy", "quantity": 2, "unit": "L",
         "purchase_date": (now - timedelta(days=1)).isoformat(),
         "expiry_date": (now + timedelta(days=1)).isoformat(), "status": "expiring",
         "cost_per_unit": 28, "store": "Milk Basket"},
        {"name": "Onions", "category": "Produce", "quantity": 3, "unit": "kg",
         "purchase_date": (now - timedelta(days=10)).isoformat(),
         "expiry_date": (now + timedelta(days=14)).isoformat(), "status": "fresh",
         "cost_per_unit": 35, "store": "DMart"},
        {"name": "Coconut Oil", "category": "Cooking", "quantity": 1, "unit": "L",
         "purchase_date": (now - timedelta(days=22)).isoformat(),
         "expiry_date": (now + timedelta(days=160)).isoformat(), "status": "fresh",
         "cost_per_unit": 210, "store": "BigBasket"},
        {"name": "Curd", "category": "Dairy", "quantity": 500, "unit": "g",
         "purchase_date": (now - timedelta(days=2)).isoformat(),
         "expiry_date": (now + timedelta(days=2)).isoformat(), "status": "expiring",
         "cost_per_unit": 45, "store": "Milk Basket"},
        {"name": "Atta (Wheat Flour)", "category": "Grains", "quantity": 5, "unit": "kg",
         "purchase_date": (now - timedelta(days=15)).isoformat(),
         "expiry_date": (now + timedelta(days=90)).isoformat(), "status": "fresh",
         "cost_per_unit": 55, "store": "DMart"},
        {"name": "Eggs", "category": "Dairy", "quantity": 12, "unit": "pcs",
         "purchase_date": (now - timedelta(days=5)).isoformat(),
         "expiry_date": (now + timedelta(days=10)).isoformat(), "status": "fresh",
         "cost_per_unit": 7, "store": "Local Vendor"},
        {"name": "Potatoes", "category": "Produce", "quantity": 2, "unit": "kg",
         "purchase_date": (now - timedelta(days=8)).isoformat(),
         "expiry_date": (now + timedelta(days=20)).isoformat(), "status": "fresh",
         "cost_per_unit": 30, "store": "Local Vendor"},
        {"name": "Green Chillies", "category": "Produce", "quantity": 200, "unit": "g",
         "purchase_date": (now - timedelta(days=3)).isoformat(),
         "expiry_date": (now + timedelta(days=4)).isoformat(), "status": "fresh",
         "cost_per_unit": 80, "store": "Local Vendor"},
        {"name": "Cumin Seeds", "category": "Spices", "quantity": 250, "unit": "g",
         "purchase_date": (now - timedelta(days=30)).isoformat(),
         "expiry_date": (now + timedelta(days=300)).isoformat(), "status": "fresh",
         "cost_per_unit": 280, "store": "BigBasket"},
        {"name": "Turmeric Powder", "category": "Spices", "quantity": 200, "unit": "g",
         "purchase_date": (now - timedelta(days=30)).isoformat(),
         "expiry_date": (now + timedelta(days=300)).isoformat(), "status": "fresh",
         "cost_per_unit": 160, "store": "BigBasket"},
        {"name": "Chicken Breast", "category": "Meat", "quantity": 1, "unit": "kg",
         "purchase_date": (now - timedelta(days=1)).isoformat(),
         "expiry_date": (now + timedelta(days=2)).isoformat(), "status": "expiring",
         "cost_per_unit": 280, "store": "Licious"},
        {"name": "Sugar", "category": "Grains", "quantity": 1, "unit": "kg",
         "purchase_date": (now - timedelta(days=20)).isoformat(),
         "expiry_date": (now + timedelta(days=180)).isoformat(), "status": "fresh",
         "cost_per_unit": 45, "store": "DMart"},
        {"name": "Tea Leaves", "category": "Beverages", "quantity": 250, "unit": "g",
         "purchase_date": (now - timedelta(days=10)).isoformat(),
         "expiry_date": (now + timedelta(days=180)).isoformat(), "status": "fresh",
         "cost_per_unit": 320, "store": "BigBasket"},
        {"name": "Ginger", "category": "Produce", "quantity": 200, "unit": "g",
         "purchase_date": (now - timedelta(days=4)).isoformat(),
         "expiry_date": (now + timedelta(days=10)).isoformat(), "status": "fresh",
         "cost_per_unit": 120, "store": "Local Vendor"},
        {"name": "Garlic", "category": "Produce", "quantity": 200, "unit": "g",
         "purchase_date": (now - timedelta(days=6)).isoformat(),
         "expiry_date": (now + timedelta(days=12)).isoformat(), "status": "fresh",
         "cost_per_unit": 140, "store": "Local Vendor"},
        {"name": "Butter", "category": "Dairy", "quantity": 500, "unit": "g",
         "purchase_date": (now - timedelta(days=7)).isoformat(),
         "expiry_date": (now + timedelta(days=30)).isoformat(), "status": "fresh",
         "cost_per_unit": 260, "store": "BigBasket"},
    ]
    await db.db["inventory"].insert_many(inventory)
    print(f"Inserted {len(inventory)} inventory items")

    # ── Receipts (3) ──
    receipts = [
        {"store": "BigBasket", "date": (now - timedelta(days=4)).isoformat(),
         "items": ["Basmati Rice", "Paneer", "Coconut Oil", "Cumin Seeds", "Tea Leaves", "Butter"],
         "total": 2340, "payment_method": "UPI", "category": "Groceries"},
        {"store": "DMart", "date": (now - timedelta(days=7)).isoformat(),
         "items": ["Toor Dal", "Onions", "Atta", "Sugar"],
         "total": 1890, "payment_method": "Card", "category": "Groceries"},
        {"store": "Reliance Fresh", "date": (now - timedelta(days=10)).isoformat(),
         "items": ["Tomatoes", "Potatoes", "Green Chillies"],
         "total": 780, "payment_method": "Cash", "category": "Produce"},
    ]
    await db.db["receipts"].insert_many(receipts)
    print(f"Inserted {len(receipts)} receipts")

    # ── Financial Ledger ──
    ledger = [
        {"date": (now - timedelta(days=4)).isoformat(), "merchant": "BigBasket",
         "amount": 2340, "category": "Groceries", "type": "expense"},
        {"date": (now - timedelta(days=7)).isoformat(), "merchant": "DMart",
         "amount": 1890, "category": "Groceries", "type": "expense"},
        {"date": (now - timedelta(days=10)).isoformat(), "merchant": "Reliance Fresh",
         "amount": 780, "category": "Produce", "type": "expense"},
        {"date": (now - timedelta(days=12)).isoformat(), "merchant": "Milk Basket",
         "amount": 450, "category": "Dairy", "type": "expense"},
        {"date": (now - timedelta(days=14)).isoformat(), "merchant": "Swiggy Instamart",
         "amount": 990, "category": "Mixed", "type": "expense"},
    ]
    await db.db["financial_ledger"].insert_many(ledger)
    print(f"Inserted {len(ledger)} ledger entries")

    # ── User Profile ──
    await db.db["user_profile"].insert_one({
        "name": "Harsh",
        "annual_salary": 1800000,
        "tax_regime": "new",
        "diet": "Vegetarian",
        "calorie_target": 1800,
        "household_size": 1,
        "created_at": now.isoformat(),
    })
    print("Inserted user profile")

    # ── Warranties (3) ──
    warranties = [
        {"product": "Samsung Galaxy S24", "brand": "Samsung", "category": "Electronics",
         "purchase_date": (now - timedelta(days=180)).isoformat(),
         "warranty_end": (now + timedelta(days=185)).isoformat(),
         "receipt_url": None, "status": "active"},
        {"product": "Prestige Induction Cooktop", "brand": "Prestige", "category": "Appliances",
         "purchase_date": (now - timedelta(days=365)).isoformat(),
         "warranty_end": (now + timedelta(days=365)).isoformat(),
         "receipt_url": None, "status": "active"},
        {"product": "Bosch Washing Machine", "brand": "Bosch", "category": "Appliances",
         "purchase_date": (now - timedelta(days=700)).isoformat(),
         "warranty_end": (now - timedelta(days=10)).isoformat(),
         "receipt_url": None, "status": "expired"},
    ]
    await db.db["warranties"].insert_many(warranties)
    print(f"Inserted {len(warranties)} warranties")

    # ── Carbon Log ──
    carbon_entries = [
        {"month": "2026-01", "total_co2_kg": 24.5, "breakdown": {"Meat": 10.2, "Dairy": 6.1, "Grains": 4.8, "Produce": 2.2, "Other": 1.2}},
        {"month": "2026-02", "total_co2_kg": 22.1, "breakdown": {"Meat": 9.0, "Dairy": 5.8, "Grains": 4.2, "Produce": 2.0, "Other": 1.1}},
        {"month": "2026-03", "total_co2_kg": 20.8, "breakdown": {"Meat": 8.5, "Dairy": 5.2, "Grains": 4.0, "Produce": 2.1, "Other": 1.0}},
        {"month": "2026-04", "total_co2_kg": 19.2, "breakdown": {"Meat": 7.8, "Dairy": 4.8, "Grains": 3.6, "Produce": 2.0, "Other": 1.0}},
        {"month": "2026-05", "total_co2_kg": 18.9, "breakdown": {"Meat": 7.5, "Dairy": 4.6, "Grains": 3.8, "Produce": 2.0, "Other": 1.0}},
        {"month": "2026-06", "total_co2_kg": 18.4, "breakdown": {"Meat": 8.2, "Dairy": 4.1, "Grains": 2.8, "Produce": 2.1, "Other": 1.2}},
    ]
    await db.db["carbon_log"].insert_many(carbon_entries)
    print(f"Inserted {len(carbon_entries)} carbon log entries")

    # ── Nutrition Log ──
    nutrition = [
        {"date": (now - timedelta(days=i)).isoformat(),
         "calories": 1450 + (i * 30) % 200,
         "protein_g": 45 + (i * 3) % 15,
         "carbs_g": 180 + (i * 5) % 30,
         "fat_g": 32 + (i * 2) % 10,
         "target_calories": 1800}
        for i in range(7)
    ]
    await db.db["nutrition_log"].insert_many(nutrition)
    print(f"Inserted {len(nutrition)} nutrition log entries")

    await db.close()
    print("\nDatabase seeded successfully!")


if __name__ == "__main__":
    asyncio.run(seed())
