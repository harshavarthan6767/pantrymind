import asyncio
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(override=True)

MODEL = os.getenv("GEMINI_LIVE_MODEL", "gemini-3.1-flash-live-preview")

async def main():
    use_vertex = os.getenv("GEMINI_BACKEND", "vertex").lower() == "vertex"
    if use_vertex:
        client = genai.Client(
            vertexai=True,
            project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
        )
    else:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("Missing GEMINI_API_KEY or GOOGLE_API_KEY")
        client = genai.Client(api_key=api_key)

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=types.Content(
            parts=[types.Part.from_text(text="You are a voice test assistant. Say: I heard you clearly.")]
        )
    )

    print("Connecting to model:", MODEL)

    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            print("Connected. Sending text input...")

            await session.send_realtime_input(text="Hello, can you hear me?")

            async for msg in session.receive():
                print("MSG TYPE:", type(msg).__name__)

                setup_complete = getattr(msg, "setup_complete", None)
                if setup_complete:
                    print("SETUP COMPLETE")
                    continue

                if getattr(msg, "server_content", None) and getattr(msg.server_content, "model_turn", None):
                    for part in msg.server_content.model_turn.parts:
                        if getattr(part, "inline_data", None):
                            print("AUDIO CHUNK:", len(part.inline_data.data), getattr(part.inline_data, "mime_type", ""))
                            return

                        if getattr(part, "text", None):
                            print("TEXT:", part.text)

                if getattr(msg, "server_content", None) and getattr(msg.server_content, "turn_complete", False):
                    print("TURN COMPLETE")
                    return
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
