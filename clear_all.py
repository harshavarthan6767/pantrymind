import asyncio
from dotenv import load_dotenv
load_dotenv()
from services.db_service import MongoDBService
from bson import ObjectId

async def main():
    db = MongoDBService()
    await db.connect()
    items = await db.find('inventory', {})
    for item in items:
        await db.update_one('inventory', {'_id': ObjectId(item['_id'])}, {'$unset': {'image_url': ''}})
    print("Cleared all URLs")

if __name__ == "__main__":
    asyncio.run(main())
