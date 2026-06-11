import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
load_dotenv()

async def test():
    db = AsyncIOMotorClient(os.getenv('MONGODB_URI'))[os.getenv('MONGODB_DATABASE')]
    receipts = await db.receipts.find().sort('date', -1).to_list(10)
    print('RECEIPTS:')
    for r in receipts:
        print(r)

asyncio.run(test())
