import os
from google.adk.agents import LlmAgent
from adk.mcp.mongodb_mcp import (
    create_governed_insert_one,
    create_governed_insert_many
)
from adk.tools.receipt_tools import (
    parse_receipt_image,         # wraps existing Gemini vision call
    calculate_expiry_batch,      # runs expiry rules on all items
    build_inventory_documents,   # shapes items for insertMany
    build_ledger_entry,          # shapes receipt total for ledger
)
from google.adk.tools import FunctionTool

RECEIPT_SYSTEM_PROMPT = """
You are the PantryMind Receipt Scanner. You process uploaded receipt images and 
populate the inventory and financial ledger.

## WORKFLOW (always in this exact order)
1. Call parse_receipt_image(image_data) to extract items + receipt total
2. Call calculate_expiry_batch(items) to add expiry dates to each item
3. Call build_inventory_documents(items) to shape for MongoDB
4. Call insertMany(collection="inventory", documents=<inventory_docs>)
5. Call build_ledger_entry(receipt_meta) to shape the expense entry
6. Call insertOne(collection="financial_ledger", document=<ledger_entry>)
7. Call insertOne(collection="receipts", document=<receipt_meta>)
8. Report to user: "Scanned ✅ — X items added to inventory. ₹Y logged as expense."

## CRITICAL RULES
- Always complete ALL steps before reporting success
- If parse_receipt_image fails, report the error and stop (do not write partial data)
- Each item must have: name, category, sub_category, dietary_flag, quantity, unit,
  purchase_date, expiry_date, safe_expiry_date, status, is_consumed (false), source ("receipt_scan")
- The ledger entry type must be "expense" and category "groceries" by default
"""

def create_receipt_agent() -> LlmAgent:
    return LlmAgent(
        name="receipt_agent",
        model=os.getenv("RECEIPT_MODEL", "gemini-3.1-pro"),
        description="Scans and parses uploaded receipt images into the pantry inventory and finance ledger.",
        instruction=RECEIPT_SYSTEM_PROMPT,
        tools=[
            create_governed_insert_one("receipt_agent"),
            create_governed_insert_many("receipt_agent"),
            FunctionTool(parse_receipt_image),
            FunctionTool(calculate_expiry_batch),
            FunctionTool(build_inventory_documents),
            FunctionTool(build_ledger_entry),
        ]
    )
