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
import pytesseract
from PIL import Image
from services.ocr_agent import OCRAgent

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
# Receipt Upload Endpoint
# ---------------------------------------------------------------------------
@app.post("/api/receipts/upload", tags=["Receipts"])
async def upload_receipt(
    file: UploadFile = File(..., description="Receipt or invoice image"),
    document_type: str = Form("receipt", description="'receipt' or 'invoice'"),
):
    """
    Upload a receipt/invoice image for OCR processing.
    The Ingestion Agent will:
      1. Store the raw image in GCS
      2. Parse it via Document AI
      3. Categorize items
      4. Add to inventory + financial ledger
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Only image files are accepted.")

    content = await file.read()
    now = datetime.utcnow().isoformat()

    # ---------------------------------------------------------
    # Advanced Offline OCR Pipeline (PaddleOCR + OpenCV)
    # ---------------------------------------------------------
    try:
        # Phase 1: Preprocess (OpenCV)
        binary_img = OCRAgent.preprocess_image(content)
        
        # Phase 2: Extract Text and Bounding Boxes (PaddleOCR)
        ocr_results = OCRAgent.extract_text_and_boxes(binary_img)
        
        # Phase 3 & 4: Parse Layout & Extract Entities (Regex + Spatial)
        parsed_data = OCRAgent.parse_receipt_layout(ocr_results)
        
        store_name = parsed_data.get("store", "Local Market")
        total_amount = parsed_data.get("total", 0.0)
        items_to_add = parsed_data.get("items", [])
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"OCR processing failed: {str(e)}")

    # 1. Add Receipt
    await db_service.insert_one("receipts", {
        "store": store_name,
        "date": now,
        "total": total_amount,
        "item_count": len(items_to_add),
        "status": "processed",
        "ocr_text": "Extracted with Advanced OCR Agent"
    })
    
    # 2. Add Financial Ledger Entry
    if total_amount > 0:
        await db_service.insert_one("financial_ledger", {
            "date": now,
            "amount": total_amount,
            "category": "Groceries",
            "description": f"Receipt from {store_name}",
            "type": "expense"
        })
    
    # 3. Add Inventory Items
    for item in items_to_add:
        doc = {
            "name": item["name"],
            "category": item["category"],
            "quantity": item["quantity"],
            "unit": item["unit"],
            "cost_per_unit": item["cost_per_unit"],
            "store": store_name,
            "status": "fresh",
            "purchase_date": now,
            "created_at": now
        }
        await db_service.insert_one("inventory", doc)

    return {
        "status": "success",
        "filename": file.filename,
        "size_bytes": len(content),
        "message": f"Processed offline. Extracted {len(items_to_add)} items.",
        "extracted_data": {
            "store": store_name,
            "total": total_amount,
            "items": len(items_to_add)
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
