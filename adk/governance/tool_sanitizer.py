"""
adk/governance/tool_sanitizer.py — Phase 3 · Day 4
====================================================
Sanitizes tool arguments before they hit MongoDB.

Goals:
  1. Strip fields that agents shouldn't be able to inject (_id, created_at, source)
  2. Enforce max document size
  3. Validate required fields per collection
  4. Strip $where and JS injection operators
"""
import logging
import json

logger = logging.getLogger("pantrymind.sanitizer")

MAX_DOC_SIZE_BYTES = 4096  # 4 KB per document max from agent

# Fields the agent is not allowed to set (system-owned)
PROTECTED_FIELDS = {"_id", "created_at", "updated_at", "source", "enrichment_status"}

# Fields that must NOT contain MongoDB operators if injected by an agent
BLOCKED_OPERATORS = {"$where", "$function", "$accumulator"}

# Required fields per collection for agent-generated documents
REQUIRED_FIELDS: dict[str, set[str]] = {
    "inventory": {"name", "quantity", "unit", "category"},
    "financial_ledger": {"amount", "category", "type"},
    "receipts": {"store", "total"},
}


def sanitize_document(collection: str, document: dict, agent_name: str = "unknown") -> dict:
    """
    Sanitize a single document before it's inserted/updated.
    Returns cleaned document.
    Raises ValueError if the document fails validation.
    """
    if not isinstance(document, dict):
        raise ValueError(f"Document must be a dict, got {type(document)}")

    # 1. Size check (pre-strip)
    raw_size = len(json.dumps(document, default=str))
    if raw_size > MAX_DOC_SIZE_BYTES:
        raise ValueError(
            f"Document too large: {raw_size} bytes (max {MAX_DOC_SIZE_BYTES}). "
            f"Agent '{agent_name}' may be embedding raw data."
        )

    # 2. Strip protected fields
    cleaned = {k: v for k, v in document.items() if k not in PROTECTED_FIELDS}
    removed = set(document.keys()) - set(cleaned.keys())
    if removed:
        logger.warning(f"Sanitizer stripped protected fields {removed} from agent '{agent_name}'")

    # 3. Block injection operators
    _check_for_operators(cleaned, agent_name)

    # 4. Validate required fields
    required = REQUIRED_FIELDS.get(collection, set())
    missing = required - set(cleaned.keys())
    if missing:
        raise ValueError(f"Document missing required fields for {collection}: {missing}")

    return cleaned


def sanitize_query(query: dict, agent_name: str = "unknown") -> dict:
    """
    Sanitize a query filter — blocks JS execution operators.
    """
    if not isinstance(query, dict):
        raise ValueError("Query must be a dict")
    _check_for_operators(query, agent_name)
    return query


def _check_for_operators(obj: dict, agent_name: str, depth: int = 0) -> None:
    """Recursively check for blocked MongoDB operators."""
    if depth > 10:
        return  # Avoid infinite recursion on deeply nested docs

    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in BLOCKED_OPERATORS:
                raise ValueError(
                    f"Blocked operator '{key}' detected in document from agent '{agent_name}'. "
                    "This may indicate a prompt injection attempt."
                )
            _check_for_operators(value, agent_name, depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            _check_for_operators(item, agent_name, depth + 1)
