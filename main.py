"""
PantryMind — Personal AI Life Management Agent
FastAPI application entry point.

Architecture:
  User → FastAPI → Root Orchestrator Agent (Google ADK)
    → Ingestion Agent (Receipt OCR)
    → Inventory Agent (MongoDB CRUD via MCP)
    → Financial Agent (Tax + Budgeting)
    → Dietary Agent (Chef Chatbot + PuLP)
    → Expiry Agent (Food Spoilage Prediction)
    → Analytics Agent (Warranty, Behavior, Carbon, Nutrition, Restock)
"""

import os
import io
import re
import json
import base64
import logging
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from pydantic import BaseModel
from bson import ObjectId
from google import genai
from google.genai import types as genai_types
from PIL import Image



load_dotenv()

from services.db_service import MongoDBService

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("pantrymind")

# ---------------------------------------------------------------------------
# Lifespan — connect/disconnect MongoDB
# ---------------------------------------------------------------------------
db_service = MongoDBService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: connect to MongoDB Atlas. Shutdown: close connection."""
    await db_service.connect()
    logger.info("MongoDB Atlas connected.")
    yield
    await db_service.close()
    logger.info("MongoDB Atlas disconnected.")


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="PantryMind",
    description="Personal AI Life Management Agent — Receipt scanning, inventory, "
    "meal planning, financial tracking, and smart analytics.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["System"])
async def health_check():
    """Health check — verifies MongoDB connectivity."""
    try:
        await db_service.ping()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": str(e)},
        )


# ---------------------------------------------------------------------------
# Gemini VLM Receipt Extraction Engine
# ---------------------------------------------------------------------------

# Configure the Gemini client (new google-genai SDK)
_gemini_api_key = os.getenv("GEMINI_API_KEY", "")
if _gemini_api_key:
    _gemini_client = genai.Client(api_key=_gemini_api_key)
    logger.info("Gemini API client initialized.")
else:
    _gemini_client = None
    logger.warning("GEMINI_API_KEY not set — receipt scanning will fail.")

# Strict JSON schema for constrained decoding (OpenAPI-subset)
RECEIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "storeName": {
            "type": "string",
            "description": "The registered name of the retail store. No address."
        },
        "items": {
            "type": "array",
            "description": "List of grocery line items ONLY. Never include taxes, subtotals, discounts, or rounding here.",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Clean product name. Strip all weights, sizes, package types."},
                    "quantity": {"type": "number", "description": "Numerical quantity. Default 1 if not stated."},
                    "unit": {"type": "string", "description": "Unit: kg, g, ml, L, unit, pcs, lbs, packet."},
                    "total_price": {"type": "number", "description": "Final billed price for this line item."}
                },
                "required": ["name", "quantity", "unit", "total_price"]
            }
        },
        "taxes": {
            "type": "object",
            "description": "Statutory tax data only. Never put taxes in the items array.",
            "properties": {
                "CGST": {"type": "number", "description": "Central GST amount. 0 if absent."},
                "SGST": {"type": "number", "description": "State GST amount. 0 if absent."},
                "IGST": {"type": "number", "description": "Integrated GST amount. 0 if absent."}
            },
            "required": ["CGST", "SGST", "IGST"]
        },
        "subtotal": {"type": "number", "description": "Pre-tax total of all grocery items."},
        "grandTotal": {"type": "number", "description": "Final amount paid including all taxes."}
    },
    "required": ["storeName", "items", "taxes", "subtotal", "grandTotal"]
}

GEMINI_META_PROMPT = """You are an expert data extraction agent specializing in Indian retail and grocery receipts.
Your task: deeply analyze the provided receipt image and extract transactional data with perfect accuracy.

CRITICAL EXTRACTION PROTOCOLS:
1. ENTITY DECOMPOSITION: Deconstruct complex product strings.
   - 'Tata Salt 1kg' → name='Tata Salt', quantity=1, unit='kg'
   - 'Amul Milk 500ml' → name='Amul Milk', quantity=500, unit='ml'
   - Strip ALL weights, volumes, sizes, container types from the 'name' field.
2. STRICT TAX ISOLATION: CGST, SGST, IGST, VAT, Cess, and 'Rounding Off' must NEVER
   appear in the 'items' array. Place them exclusively in the 'taxes' object.
   If a specific tax is absent, set its value to 0.
3. HALLUCINATION PREVENTION: Ignore creases, folds, smudges, barcodes, logos,
   and watermarks. Do NOT invent data. Extract only clear transactional text.
4. INFERENTIAL DEFAULTS: If a grocery product has no explicit quantity, default
   quantity=1 and unit='unit'.
5. PRICE PRECISION: If a receipt shows both unit price and total price on the same
   line, use the TOTAL price for 'total_price'.

Return the data strictly conforming to the requested JSON schema."""


async def extract_receipt_with_gemini(image_bytes: bytes, mime_type: str) -> dict:
    """Call Gemini with constrained JSON schema to extract structured receipt data."""
    if not _gemini_client:
        raise RuntimeError("Gemini client is not initialized. Set GEMINI_API_KEY.")

    # Resize to max 1600px on longest edge to reduce token cost
    img = Image.open(io.BytesIO(image_bytes))
    max_edge = 1600
    if max(img.width, img.height) > max_edge:
        ratio = max_edge / max(img.width, img.height)
        img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        image_bytes = buf.getvalue()
        mime_type = "image/jpeg"

    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    response = await _gemini_client.aio.models.generate_content(
        model=model_name,
        contents=[
            GEMINI_META_PROMPT,
            genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        ],
        config=genai_types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RECEIPT_SCHEMA,
            temperature=0.1,
            top_p=0.8,
            top_k=10,
        )
    )
    return json.loads(response.text)


# ---------------------------------------------------------------------------
# Receipt Upload Endpoint  (image → Gemini → MongoDB)
# ---------------------------------------------------------------------------
@app.post("/api/receipts/upload", tags=["Receipts"])
async def upload_receipt(file: UploadFile = File(...)):
    """
    Accept a raw receipt image, extract structured data via Gemini 1.5 Flash
    (strict JSON schema / constrained decoding), and persist to MongoDB.
    """
    if not _gemini_client:
        raise HTTPException(503, "Gemini API key is not configured on the server.")

    now = datetime.utcnow().isoformat()

    # 1. Read uploaded bytes
    image_bytes = await file.read()
    mime_type = file.content_type or "image/jpeg"

    # 2. Extract with Gemini VLM
    try:
        extracted = await extract_receipt_with_gemini(image_bytes, mime_type)
        logger.info(f"Gemini extracted {len(extracted.get('items', []))} items from receipt.")
    except Exception as e:
        logger.error(f"Gemini extraction failed: {e}")
        raise HTTPException(500, f"AI extraction failed: {str(e)}")

    store_name  = extracted.get("storeName", "Unknown Store")
    grand_total = float(extracted.get("grandTotal") or 0.0)
    subtotal    = float(extracted.get("subtotal") or 0.0)
    taxes       = extracted.get("taxes", {"CGST": 0, "SGST": 0, "IGST": 0})
    items       = extracted.get("items", [])

    # 3. Persist receipt document
    await db_service.insert_one("receipts", {
        "store": store_name,
        "date": now,
        "total": grand_total,
        "subtotal": subtotal,
        "taxes": taxes,
        "item_count": len(items),
        "status": "processed",
        "engine": "gemini-vision"
    })

    # 4. Persist financial ledger entry
    if grand_total > 0:
        await db_service.insert_one("financial_ledger", {
            "date": now,
            "amount": grand_total,
            "category": "Groceries",
            "description": f"Receipt from {store_name}",
            "type": "expense"
        })

    # 5. Persist inventory items
    for item in items:
        qty   = float(item.get("quantity") or 1)
        price = float(item.get("total_price") or 0.0)
        await db_service.insert_one("inventory", {
            "name": str(item.get("name", "Unknown"))[:60],
            "category": "Groceries",
            "quantity": qty,
            "unit": str(item.get("unit", "unit")),
            "cost_per_unit": round(price / qty, 2) if qty > 0 else price,
            "store": store_name,
            "status": "fresh",
            "purchase_date": now,
            "created_at": now
        })

    return {
        "status": "success",
        "message": f"Gemini Vision extracted {len(items)} items from receipt.",
        "extracted_data": {
            "store": store_name,
            "subtotal": subtotal,
            "taxes": taxes,
            "grandTotal": grand_total,
            "items": len(items)
        }
    }


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------
class InventoryItem(BaseModel):
    name: str
    category: str
    quantity: float
    unit: str
    purchase_date: str | None = None
    expiry_date: str | None = None
    status: str = "fresh"
    cost_per_unit: float = 0
    store: str = ""


class ChatMessage(BaseModel):
    message: str


@app.post("/api/chat", tags=["Agent"])
async def chat(body: ChatMessage):
    """
    Send a natural language message to the PantryMind Root Orchestrator.
    Currently returns a mock echo response until agent integration is wired.
    """
    return {
        "status": "ok",
        "user_message": body.message,
        "reply": f"[PantryMind] I received your message: '{body.message}'. "
                 "Agent integration is pending -- this is a mock response.",
    }


# ---------------------------------------------------------------------------
# Inventory Endpoints (REST fallback for frontend)
# ---------------------------------------------------------------------------
@app.get("/api/inventory", tags=["Inventory"])
async def get_inventory(category: str | None = None):
    """Retrieve current inventory, optionally filtered by category."""
    query = {}
    if category:
        query["category"] = category
    items = await db_service.find("inventory", query)
    return {"items": items, "count": len(items)}


@app.post("/api/inventory", tags=["Inventory"])
async def add_inventory_item(item: InventoryItem):
    """Add a new item to the inventory."""
    doc = item.model_dump()
    doc["created_at"] = datetime.utcnow().isoformat()
    inserted_id = await db_service.insert_one("inventory", doc)
    doc["_id"] = inserted_id
    return {"status": "created", "item": doc}


@app.put("/api/inventory/{item_id}", tags=["Inventory"])
async def update_inventory_item(item_id: str, item: InventoryItem):
    """Update an existing inventory item by its ObjectId."""
    try:
        oid = ObjectId(item_id)
    except Exception:
        raise HTTPException(400, "Invalid item ID format.")

    modified = await db_service.update_one(
        "inventory",
        {"_id": oid},
        {"$set": item.model_dump()},
    )
    if modified == 0:
        raise HTTPException(404, "Item not found.")
    return {"status": "updated", "item_id": item_id}


@app.delete("/api/inventory/{item_id}", tags=["Inventory"])
async def delete_inventory_item(item_id: str):
    """Delete an inventory item by its ObjectId."""
    try:
        oid = ObjectId(item_id)
    except Exception:
        raise HTTPException(400, "Invalid item ID format.")

    deleted = await db_service.delete_one("inventory", {"_id": oid})
    if deleted == 0:
        raise HTTPException(404, "Item not found.")
    return {"status": "deleted", "item_id": item_id}


@app.post("/api/inventory/consume", tags=["Inventory"])
async def consume_item(
    item_name: str = Form(...),
    quantity: float = Form(1.0),
):
    """Mark an item as consumed -- decrements inventory and logs to history."""
    # TODO: Wire to Inventory Agent
    return {
        "status": "consumed",
        "item_name": item_name,
        "quantity": quantity,
        "message": "Consumption logged. Inventory updated.",
    }


# ---------------------------------------------------------------------------
# Dashboard Stats
# ---------------------------------------------------------------------------
@app.get("/api/dashboard/stats", tags=["Dashboard"])
async def get_dashboard_stats():
    """Aggregate dashboard statistics from multiple collections."""
    # Total inventory count
    all_items = await db_service.find("inventory", {})
    total_items = len(all_items)

    # Items expiring soon
    expiring_items = await db_service.find("inventory", {"status": "expiring"})
    expiring_soon = len(expiring_items)

    # Monthly spending from financial_ledger (current month)
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    pipeline = [
        {"$match": {"date": {"$gte": month_start.isoformat()}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]
    agg_result = await db_service.aggregate("financial_ledger", pipeline)
    monthly_spending = agg_result[0]["total"] if agg_result else 0

    # Recent receipts (last 3)
    recent_receipts = await db_service.find(
        "receipts", {}, limit=3, sort=[("date", -1)]
    )

    return {
        "total_items": total_items,
        "expiring_soon": expiring_soon,
        "monthly_spending": monthly_spending,
        "recent_receipts": recent_receipts,
        "expiring_items": expiring_items,
    }


# ---------------------------------------------------------------------------
# Receipts
# ---------------------------------------------------------------------------
@app.get("/api/receipts", tags=["Receipts"])
async def get_receipts():
    """Return all receipts sorted by date descending."""
    receipts = await db_service.find(
        "receipts", {}, sort=[("date", -1)]
    )
    return {"receipts": receipts, "count": len(receipts)}


# ---------------------------------------------------------------------------
# Finance — Transactions
# ---------------------------------------------------------------------------
@app.get("/api/finance/transactions", tags=["Finance"])
async def get_finance_transactions():
    """Return all financial ledger entries sorted by date descending."""
    transactions = await db_service.find(
        "financial_ledger", {}, sort=[("date", -1)]
    )
    return {"transactions": transactions, "count": len(transactions)}


# ---------------------------------------------------------------------------
# Financial Endpoints
# ---------------------------------------------------------------------------
@app.post("/api/finance/set-salary", tags=["Finance"])
async def set_salary(
    monthly_salary: float = Form(..., description="Gross monthly salary in INR"),
    tax_regime: str = Form("new", description="'new' or 'old'"),
):
    """Set or update the user's salary and tax regime preference."""
    # TODO: Wire to Financial Agent
    return {
        "status": "saved",
        "monthly_salary": monthly_salary,
        "tax_regime": tax_regime,
    }


@app.get("/api/finance/summary", tags=["Finance"])
async def get_financial_summary():
    """Get financial summary: tax computation, spending, disposable income."""
    # TODO: Wire to Financial Agent
    return {"message": "Financial summary endpoint — wire to Financial Agent."}


# ---------------------------------------------------------------------------
# Analytics Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/analytics/carbon", tags=["Analytics"])
async def get_carbon_footprint():
    """Get carbon footprint entries sorted by month."""
    entries = await db_service.find(
        "carbon_log", {}, sort=[("month", -1)]
    )
    return {"carbon_log": entries, "count": len(entries)}


@app.get("/api/analytics/nutrition", tags=["Analytics"])
async def get_nutrition_report():
    """Get nutrition log entries sorted by date."""
    entries = await db_service.find(
        "nutrition_log", {}, sort=[("date", -1)], limit=30
    )
    return {"nutrition_log": entries, "count": len(entries)}


@app.get("/api/analytics/restock", tags=["Analytics"])
async def get_restock_alerts():
    """Items likely to run out soon (low quantity or expiring)."""
    low_qty = await db_service.find(
        "inventory",
        {"$or": [{"status": "expiring"}, {"quantity": {"$lte": 1}}]},
    )
    return {"restock_items": low_qty, "count": len(low_qty)}


@app.get("/api/analytics/behavior", tags=["Analytics"])
async def get_behavior_insights():
    """Spending patterns from financial ledger."""
    transactions = await db_service.find(
        "financial_ledger", {}, sort=[("date", -1)], limit=50
    )
    # Category breakdown
    by_cat = {}
    for tx in transactions:
        cat = tx.get("category", "Other")
        by_cat[cat] = by_cat.get(cat, 0) + tx.get("amount", 0)
    return {
        "transactions": transactions,
        "category_breakdown": by_cat,
        "total_spent": sum(by_cat.values()),
    }


@app.get("/api/user/profile", tags=["User"])
async def get_user_profile():
    """Get the user profile."""
    profile = await db_service.find_one("user_profile", {})
    return {"profile": profile}


@app.get("/api/analytics/warranties", tags=["Analytics"])
async def get_warranties():
    """Get all warranties from the warranties collection."""
    warranties = await db_service.find("warranties", {})
    return {"warranties": warranties, "count": len(warranties)}


# ---------------------------------------------------------------------------
# Serve Frontend (production only — in dev, Vite handles this)
# ---------------------------------------------------------------------------
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/{full_path:path}", tags=["Frontend"])
    async def serve_spa(full_path: str):
        """SPA fallback — serve index.html for all unmatched routes."""
        file_path = static_dir / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(static_dir / "index.html")


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("APP_PORT", 8000)),
        reload=os.getenv("APP_ENV") == "development",
    )
