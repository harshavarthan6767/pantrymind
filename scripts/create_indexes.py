import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, ASCENDING, DESCENDING
import os
from dotenv import load_dotenv

load_dotenv()

import certifi

async def create_all_indexes():
    client = AsyncIOMotorClient(os.getenv("MONGODB_URI"), tlsCAFile=certifi.where())
    db = client[os.getenv("MONGODB_DATABASE", "finmind")]

    await db.inventory.create_indexes([
        IndexModel([("user_id", ASCENDING), ("status", ASCENDING)], name="user_status"),
        IndexModel([("user_id", ASCENDING), ("expiry_date", ASCENDING)], name="user_expiry"),
        IndexModel([("user_id", ASCENDING), ("category", ASCENDING)], name="user_category"),
        IndexModel([("user_id", ASCENDING), ("name", ASCENDING)], name="user_name"),
        # Partial index for active inventory only (reduces index size)
        IndexModel(
            [("user_id", ASCENDING), ("status", ASCENDING), ("expiry_date", ASCENDING)],
            name="user_status_expiry",
            partialFilterExpression={"status": {"$in": ["fresh", "expiring"]}}
        ),
    ])
    await db.financial_ledger.create_indexes([
        IndexModel([("user_id", ASCENDING), ("type", ASCENDING), ("date", DESCENDING)], name="user_type_date"),
        IndexModel([("user_id", ASCENDING), ("category", ASCENDING), ("date", DESCENDING)], name="user_category_date"),
        IndexModel([("user_id", ASCENDING), ("date", DESCENDING)], name="user_date"),
    ])
    await db.receipts.create_indexes([
        IndexModel([("user_id", ASCENDING), ("date", DESCENDING)], name="user_date"),
    ])
    await db.warranties.create_indexes([
        IndexModel([("user_id", ASCENDING), ("expiry_date", ASCENDING)], name="user_expiry"),
    ])
    for col in ["carbon_log", "nutrition_log", "consumption_history"]:
        await db[col].create_indexes([
            IndexModel([("user_id", ASCENDING), ("date", DESCENDING)], name="user_date"),
        ])
    client.close()
    print("✅ All indexes created")

if __name__ == "__main__":
    asyncio.run(create_all_indexes())
