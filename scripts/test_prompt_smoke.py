import asyncio
import os
from google import genai
from google.genai import types
from services.voice_service import GLOBAL_VOICE_PROMPT

MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"

async def main():
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    config = types.LiveConnectConfig(
        system_instruction=types.Content(
            parts=[types.Part.from_text(text=GLOBAL_VOICE_PROMPT)]
        ),
        response_modalities=["AUDIO"],
    )

    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            print("Connected.")
            await session.send_realtime_input(text="Hello")
            async for msg in session.receive():
                print("MSG:", type(msg).__name__)
                return
    except Exception as e:
        print("Test Failed:", type(e).__name__, e)

if __name__ == "__main__":
    asyncio.run(main())
