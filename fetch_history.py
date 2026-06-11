import asyncio, json
from motor.motor_asyncio import AsyncIOMotorClient
async def main():
    client = AsyncIOMotorClient('mongodb+srv://finmind:finmind123456789@cluster0.o5h6f.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
    db = client.finmind
    docs = await db.kitchen_conversation_history.find({}).sort('timestamp', -1).limit(2).to_list(None)
    for d in docs: d['_id'] = str(d['_id'])
    print(json.dumps(docs, indent=2))
asyncio.run(main())
