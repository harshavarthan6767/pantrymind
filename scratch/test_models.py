import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

print("Checking environment variables:")
print("GEMINI_BACKEND:", os.getenv("GEMINI_BACKEND"))
print("GEMINI_MODEL:", os.getenv("GEMINI_MODEL"))
print("GEMINI_MODEL_OCR:", os.getenv("GEMINI_MODEL_OCR"))
print("GEMINI_MODEL_CHAT:", os.getenv("GEMINI_MODEL_CHAT"))
print("GEMINI_MODEL_KITCHEN:", os.getenv("GEMINI_MODEL_KITCHEN"))

try:
    from main import _gemini_client, _gemini_backend
    print(f"\nGemini Client initialized successfully using backend: {_gemini_backend}")
    if _gemini_client:
        print("Client is NOT None. Success!")
    else:
        print("Client IS None.")
except Exception as e:
    print(f"\nError initializing Gemini client: {e}")
