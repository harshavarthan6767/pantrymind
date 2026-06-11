import asyncio
from adk.runner import init_runner, get_runner
from google.genai.types import Content, Part

async def main():
    print("Init runner...")
    await init_runner()
    r = get_runner()
    print("Running ADK...")
    new_message = Content(role="user", parts=[Part(text="What should I buy?")])
    
    async for event in r.run_async(user_id="u", session_id="s", new_message=new_message):
        print("EVENT:", event)
        if getattr(event, 'content', None):
            print("CONTENT PARTS:", getattr(event.content, 'parts', None))
        if event.get_function_calls():
            print("CALLS:", event.get_function_calls())

asyncio.run(main())
