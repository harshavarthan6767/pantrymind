# scripts/embed_existing_inventory.py
# Run once after creating the index: python scripts/embed_existing_inventory.py

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()
from adk.memory.vector_memory import build_inventory_document_text, embed_text

async def backfill():
    client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
    db = client[os.getenv("MONGODB_DATABASE", "finmind")]

    items = await db.inventory.find(
        {"embedding": {"$exists": False}}
    ).to_list(None)

    print(f"Backfilling {len(items)} items...")

    for i, item in enumerate(items):
        doc_text  = build_inventory_document_text(item)
        embedding = embed_text(doc_text)
        await db.inventory.update_one(
            {"_id": item["_id"]},
            {"$set": {"embedding": embedding}}
        )
        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{len(items)}")
            await asyncio.sleep(0.6)   # text-embedding-004: ~100 req/min free

    print("Backfill complete")
    client.close()

if __name__ == "__main__":
    asyncio.run(backfill())
