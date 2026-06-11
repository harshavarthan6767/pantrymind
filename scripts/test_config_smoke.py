import asyncio
import os
from google import genai
from google.genai import types

MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"

async def main():
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    print("Test 1: Full config from voice_service.py")
    config = types.LiveConnectConfig(
        system_instruction=types.Content(
            parts=[types.Part.from_text(text="Test prompt")]
        ),
        tools=[],
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name="Puck"
                )
            )
        )
    )

    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            print("Connected 1.")
            await session.send_realtime_input(text="Hello")
            async for msg in session.receive():
                print("1 MSG TYPE:", type(msg).__name__)
    except Exception as e:
        print("Test 1 Failed:", e)

    print("\nTest 2: Without speech_config")
    config2 = types.LiveConnectConfig(
        system_instruction=types.Content(parts=[types.Part.from_text(text="Test prompt")]),
        tools=[],
        response_modalities=["AUDIO"],
    )
    try:
        async with client.aio.live.connect(model=MODEL, config=config2) as session:
            print("Connected 2.")
            await session.send_realtime_input(text="Hello")
            async for msg in session.receive():
                print("2 MSG TYPE:", type(msg).__name__)
    except Exception as e:
        print("Test 2 Failed:", e)

    print("\nTest 3: Without tools=[]")
    config3 = types.LiveConnectConfig(
        system_instruction=types.Content(parts=[types.Part.from_text(text="Test prompt")]),
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck")
            )
        )
    )
    try:
        async with client.aio.live.connect(model=MODEL, config=config3) as session:
            print("Connected 3.")
            await session.send_realtime_input(text="Hello")
            async for msg in session.receive():
                print("3 MSG TYPE:", type(msg).__name__)
    except Exception as e:
        print("Test 3 Failed:", e)

if __name__ == "__main__":
    asyncio.run(main())
