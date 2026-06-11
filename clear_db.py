import asyncio
from dotenv import load_dotenv
load_dotenv()
from services.db_service import MongoDBService

async def main():
    db = MongoDBService()
    await db.connect()
    items = await db.find('inventory', {})
    for item in items:
        # Check if URL starts with /product-images/dataset
        url = item.get('image_url')
        if url and 'dataset' in url:
            await db.update_one('inventory', {'_id': item['_id']}, {'$unset': {'image_url': ''}})
            print(f"Cleared URL for {item.get('name')}")
    print("Done clearing DB")

if __name__ == "__main__":
    asyncio.run(main())
