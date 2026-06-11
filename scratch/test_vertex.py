import os
import asyncio
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

async def test_vertex():
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION")
    model_name = "gemini-2.5-pro"

    print(f"Testing Vertex AI integration...")
    print(f"Project: {project}, Location: {location}")
    print(f"Model: {model_name}")

    client = genai.Client(vertexai=True, project=project, location=location)

    try:
        response = await client.aio.models.generate_content(
            model=model_name,
            contents="Say 'Hello Vertex AI!' if you can hear me."
        )
        print("\nSuccess! Model responded:")
        print(response.text)
    except Exception as e:
        print(f"\nError calling Vertex AI: {e}")

if __name__ == "__main__":
    asyncio.run(test_vertex())
