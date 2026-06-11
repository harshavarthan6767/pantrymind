import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)

print("Models supporting bidiGenerateContent:")
for m in client.models.list():
    actions = getattr(m, 'supported_actions', [])
    if "bidiGenerateContent" in actions:
        print(f"  {m.name}")
