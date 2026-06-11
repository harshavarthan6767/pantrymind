import asyncio
from google.adk.sessions import InMemorySessionService

async def main():
    s = InMemorySessionService()
    try:
        await s.create_session(app_name="app1", user_id="u1", session_id="s1")
        print("Created successfully.")
        res = await s.get_session(app_name="app1", user_id="u1", session_id="s1")
        print("SUCCESS:", dir(res))
    except Exception as e:
        print("ERROR:", e)

asyncio.run(main())
