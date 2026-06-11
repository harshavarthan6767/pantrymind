import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from agents.ordering_tools import simulate_platform_order
async def test():
    db = AsyncIOMotorClient('mongodb://localhost:27017').pantrymind
    print(await simulate_platform_order(db, 'default_user', [{'name': 'Test Item', 'quantity': 1}]))
asyncio.run(test())
