import asyncio, json
from motor.motor_asyncio import AsyncIOMotorClient
import os
async def main():
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(uri)
    db = client.finmind
    docs = await db.kitchen_conversation_history.find({}).sort('timestamp', -1).limit(2).to_list(None)
    for d in docs: d['_id'] = str(d['_id'])
    print(json.dumps(docs, indent=2))
asyncio.run(main())
