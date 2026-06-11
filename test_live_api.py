import asyncio
import base64
from google import genai
from google.genai import types

async def test_live():
    client = genai.Client(vertexai=True, project="pantrymind-1209", location="us-central1")
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"]
    )
    
    print("Connecting to live API...")
    try:
        async with client.aio.live.connect(model="gemini-live-2.5-flash-native-audio", config=config) as session:
            print("Connected! Sending text message: 'Hello, what can you do?'")
            await session.send(input=types.LiveClientContent(parts=[types.Part.from_text(text="Hello, what can you do?")]))
            
            print("Waiting for response...")
            async for msg in session.receive():
                print("Received message type:", type(msg))
                if msg.server_content:
                    if msg.server_content.model_turn:
                        for part in msg.server_content.model_turn.parts:
                            if part.text:
                                print("Text part:", part.text)
                            if part.inline_data:
                                print("Audio part received:", len(part.inline_data.data), "bytes")
                    if msg.server_content.turn_complete:
                        print("Turn complete! Exiting.")
                        break
    except Exception as e:
        print("Error during live session:", e)

if __name__ == "__main__":
    asyncio.run(test_live())
