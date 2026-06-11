import os
import time
import asyncio
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=key)

RECEIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "storeName": {"type": "string"},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "quantity": {"type": "number"},
                    "unit": {"type": "string"},
                    "total_price": {"type": "number"}
                },
                "required": ["name", "quantity", "unit", "total_price"]
            }
        },
        "taxes": {
            "type": "object",
            "properties": {
                "CGST": {"type": "number"},
                "SGST": {"type": "number"},
                "IGST": {"type": "number"}
            },
            "required": ["CGST", "SGST", "IGST"]
        },
        "subtotal": {"type": "number"},
        "grandTotal": {"type": "number"}
    },
    "required": ["storeName", "items", "taxes", "subtotal", "grandTotal"]
}

ocr_text = """
127.0.0.1:65195 - "GET /api/analytics/nutrition HTTP/1.1" 200 OK
Tata Salt 1kg 28.00
Amul Milk 500ml 27.00
Maggie Noodles 12.00
CGST 2.5% 1.68
SGST 2.5% 1.68
GRAND TOTAL 70.36
"""

prompt = f"Parse this receipt:\n{ocr_text}"

async def test_async():
    print("Testing async client...")
    start = time.time()
    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RECEIPT_SCHEMA,
            temperature=0.1
        )
    )
    print(f"Async client time: {time.time() - start:.2f} seconds")
    print("Response:", response.text)

asyncio.run(test_async())
