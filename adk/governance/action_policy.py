import os

ENABLE_ACTION_APPROVALS = os.getenv("ENABLE_ACTION_APPROVALS", "true").lower() == "true"
MAX_AUTO_ACTION_VALUE_INR = float(os.getenv("MAX_AUTO_ACTION_VALUE_INR", "250"))
ALLOW_DESTRUCTIVE_MCP_TOOLS = os.getenv("ALLOW_DESTRUCTIVE_MCP_TOOLS", "false").lower() == "true"
LOW_CONFIDENCE_APPROVAL_THRESHOLD = float(os.getenv("LOW_CONFIDENCE_APPROVAL_THRESHOLD", "0.72"))

def evaluate_action_policy(tool_name: str, collection: str, arguments: dict) -> dict:
    """
    Evaluates a proposed MCP MongoDB tool call against the Phase 3 Action Policy.
    Returns:
        {
            "status": "auto" | "requires_approval" | "blocked",
            "reason": str,
            "risk_level": "low" | "medium" | "high" | "critical"
        }
    """
    read_only_tools = {"find", "aggregate", "count", "distinct", "listCollections", "listIndexes"}
    destructive_tools = {"deleteOne", "deleteMany", "dropCollection", "dropDatabase", "replaceOne"}

    if tool_name in destructive_tools:
        if ALLOW_DESTRUCTIVE_MCP_TOOLS:
            return {"status": "requires_approval", "reason": "Destructive tool allowed by env config.", "risk_level": "critical"}
        return {"status": "blocked", "reason": f"Tool '{tool_name}' is blocked by policy.", "risk_level": "critical"}

    if tool_name in read_only_tools:
        return {"status": "auto", "reason": "Read-only operation.", "risk_level": "low"}

    # Evaluate writes
    if not ENABLE_ACTION_APPROVALS:
        return {"status": "auto", "reason": "Approvals disabled by config.", "risk_level": "low"}

    if tool_name in ("insertOne", "insertMany"):
        if collection == "notifications":
            return {"status": "auto", "reason": "Low-risk generated alert.", "risk_level": "low"}
        if collection == "pending_actions":
            return {"status": "auto", "reason": "System storage for approvals.", "risk_level": "low"}
        if collection == "inventory":
            return {"status": "requires_approval", "reason": "Adding items to inventory requires user confirmation.", "risk_level": "medium"}
        if collection == "financial_ledger":
            # Check cost
            doc = arguments.get("document", {})
            docs = arguments.get("documents", [])
            total_amount = doc.get("amount", 0) + sum(d.get("amount", 0) for d in docs)
            
            if total_amount > MAX_AUTO_ACTION_VALUE_INR:
                return {"status": "requires_approval", "reason": f"Financial entry above auto-approval threshold of {MAX_AUTO_ACTION_VALUE_INR} INR.", "risk_level": "high"}
            return {"status": "requires_approval", "reason": "Modifying financial ledger requires confirmation.", "risk_level": "medium"}
            
    if tool_name in ("updateOne", "updateMany"):
        return {"status": "requires_approval", "reason": "Updating records requires confirmation.", "risk_level": "medium"}

    # Default fallback for unknown writes
    return {"status": "requires_approval", "reason": f"Unknown write action '{tool_name}' requires approval.", "risk_level": "high"}
