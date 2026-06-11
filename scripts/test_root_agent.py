import asyncio
from agents.root_agent import root_agent

async def test():
    print("Testing Root Agent directly...")
    try:
        response = root_agent.run("Create a meal plan")
        print("Root Agent Response:")
        print(response.text)
    except Exception as e:
        print("Root Agent Failed:", e)

if __name__ == "__main__":
    asyncio.run(test())
