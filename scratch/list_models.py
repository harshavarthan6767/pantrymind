import os
import asyncio
from dotenv import load_dotenv
from google import genai

load_dotenv()

async def list_models():
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION")
    client = genai.Client(vertexai=True, project=project, location=location)

    try:
        print("Fetching models...")
        models = client.models.list()
        for m in models:
            if 'gemini-3' in m.name or 'gemini-2' in m.name:
                print(m.name)
    except Exception as e:
        print(f"Error fetching models: {e}")

if __name__ == "__main__":
    asyncio.run(list_models())
