import os
import time
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
TASTEE GROCERS
123 MARKET STREET, MUMBAI
TEL: 022-1234567

DATE: 03/06/2026 14:30
CASHIER: RAHUL

ITEMS:
------------------------------------------
1. TATA PREMIUM TEA 1KG         320.00
2. ASHIRVAAD ATTA 5KG           275.00
3. AMUL BUTTER 500G             265.00
4. SURF EXCEL EASY WASH 1KG     140.00
5. FORTUNE SOYABEAN OIL 1L      165.00
6. MAGGI NOODLES 12-PACK        168.00
7. BRITANNIA MARIE GOLD 250G     35.00
8. DETTOL LIQUID HANDWASH 750ML 119.00
9. HARPIC TOILET CLEANER 1L     185.00
10. COLGATE MAXFRESH 150G        95.00

SUBTOTAL:                      1767.00
CGST @ 2.5%:                     44.18
SGST @ 2.5%:                     44.18
ROUND OFF:                       -0.36
------------------------------------------
GRAND TOTAL:                   1855.00

THANK YOU FOR SHOPPING WITH US!
"""

prompt = f"Parse this receipt:\n{ocr_text}"

models = ["gemini-2.5-flash", "gemini-3.5-flash", "gemini-flash-latest", "gemini-2.0-flash-lite"]

for model in models:
    print(f"\n--- Testing {model} ---")
    start = time.time()
    try:
        response = client.models.generate_content(
            model=model,
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RECEIPT_SCHEMA,
                temperature=0.1
            )
        )
        elapsed = time.time() - start
        print(f"[{model}] Time taken: {elapsed:.2f} seconds")
        print("Response length:", len(response.text))
    except Exception as e:
        elapsed = time.time() - start
        print(f"[{model}] Failed after {elapsed:.2f} seconds. Error: {e}")
