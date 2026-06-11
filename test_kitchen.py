import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from google import genai
from services.kitchen_chat_service import KitchenChatService
from dotenv import load_dotenv
load_dotenv()

async def test():
    db_service = AsyncIOMotorClient(os.getenv('MONGODB_URI'))[os.getenv('MONGODB_DATABASE')]
    gemini = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
    service = KitchenChatService(db_service, gemini)
    reply, metadata = await service.process_message('test_session', 'default_user', '400 cal and 80 gram of protein and 20 g of fat')
    print('REPLY:', reply)

asyncio.run(test())
