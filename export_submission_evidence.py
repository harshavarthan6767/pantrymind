#!/usr/bin/env python
"""
export_submission_evidence.py — Phase 3 · Day 2
================================================
Generates a complete, self-contained hackathon evidence package:

  submission_evidence/
  ├── README.md                    ← what judges should look at first
  ├── architecture.json            ← agent hierarchy, tools, MCP integration
  ├── traces/                      ← per-session JSON traces from MongoDB
  │   ├── <session_id>.json
  │   └── ...
  ├── approvals/                   ← all pending/approved/rejected actions
  │   └── pending_actions.json
  ├── metrics/                     ← eval scores (if evaluation was run)
  │   └── eval_summary.json
  └── screenshots/                 ← placeholder for video/screenshots

Usage:
    cd D:\\pantrymind-desktop
    .venv\\Scripts\\python export_submission_evidence.py
    
    # To also run a quick live sanity check against running server:
    .venv\\Scripts\\python export_submission_evidence.py --sanity-check
"""

import os
import sys
import json
import asyncio
import argparse
import datetime
from pathlib import Path

import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = Path("submission_evidence")

ARCHITECTURE = {
    "project": "PantryMind",
    "hackathon_track": "Google Cloud Agent Builder + MongoDB MCP",
    "submission_date": datetime.datetime.utcnow().isoformat() + "Z",
    "stack": {
        "backend": "FastAPI + Python 3.13",
        "frontend": "React + Vite",
        "database": "MongoDB Atlas (via Motor async driver)",
        "mcp_server": "@mongodb-js/mcp-server-mongodb (official)",
        "agent_framework": "Google ADK (Agent Development Kit)",
        "llm": "Gemini 2.5 Flash (Vertex AI, us-central1)",
        "deployment_target": "Cloud Run"
    },
    "agent_hierarchy": {
        "pantrymind_orchestrator": {
            "model": "gemini-2.5-flash",
            "pattern": "Plan-then-Execute routing",
            "sub_agents": [
                {
                    "name": "pantry_agent",
                    "model": "gemini-2.5-flash",
                    "tools": ["MongoDB MCP read-only", "governed updateOne", "semantic_pantry_search", "calculate_expiry"],
                    "governance": "updateOne requires approval"
                },
                {
                    "name": "kitchen_chef_agent",
                    "model": "gemini-2.5-flash",
                    "tools": ["MongoDB MCP read-only", "run_meal_optimizer (PuLP)", "get_nutrition_for_items"],
                    "governance": "read-only — no writes"
                },
                {
                    "name": "finance_agent",
                    "model": "gemini-2.5-flash",
                    "tools": ["MongoDB MCP read-only", "parse_date_range", "compute_budget_summary"],
                    "governance": "read-only — no writes"
                },
                {
                    "name": "receipt_agent",
                    "model": "gemini-2.5-flash",
                    "tools": ["MongoDB MCP read-only", "governed insertOne", "governed insertMany", "parse_receipt_image"],
                    "governance": "all inserts require approval (medium risk)"
                },
                {
                    "name": "shopping_agent",
                    "model": "gemini-2.5-flash",
                    "tools": ["MongoDB MCP read-only", "compute_ingredient_gaps", "prioritize_shopping_list"],
                    "governance": "read-only — no writes"
                }
            ]
        }
    },
    "phase3_features": {
        "governance_layer": {
            "action_policy": "adk/governance/action_policy.py",
            "pending_actions": "adk/governance/pending_actions.py",
            "approval_executor": "adk/governance/approval_executor.py",
            "api": "GET/POST /api/approvals"
        },
        "evidence_tracing": {
            "logger": "adk/demo/evidence_logger.py",
            "api": "GET /api/traces/{session_id}",
            "frontend": "frontend/src/components/TraceTimeline.jsx"
        },
        "mongodb_mcp": {
            "server": "@mongodb-js/mcp-server-mongodb",
            "connection": "StdioServerParameters via npx",
            "toolset_split": "read-only toolset + governed write function tools",
            "collections": ["inventory", "receipts", "financial_ledger", "warranties", "user_profile", "pending_actions", "agent_traces"]
        }
    }
}


async def export_traces(db, output_dir: Path):
    """Export all agent traces grouped by session."""
    traces_dir = output_dir / "traces"
    traces_dir.mkdir(exist_ok=True)

    # Get unique session IDs
    pipeline = [
        {"$group": {"_id": "$session_id"}},
        {"$limit": 50}
    ]
    sessions = [doc["_id"] async for doc in db["agent_traces"].aggregate(pipeline)]
    
    all_sessions = []
    for session_id in sessions:
        events = []
        async for doc in db["agent_traces"].find({"session_id": session_id}).sort("ts", 1):
            doc["_id"] = str(doc["_id"])
            events.append(doc)
        
        session_file = traces_dir / f"{session_id.replace('/', '_')}.json"
        session_file.write_text(json.dumps(events, indent=2, default=str))
        all_sessions.append({"session_id": session_id, "event_count": len(events)})
        print(f"  ✓ Exported {len(events)} events for session {session_id[:16]}...")
    
    return all_sessions


async def export_approvals(db, output_dir: Path):
    """Export all pending actions / governance records."""
    approvals_dir = output_dir / "approvals"
    approvals_dir.mkdir(exist_ok=True)

    actions = []
    async for doc in db["pending_actions"].find({}).sort("created_at", -1).limit(200):
        doc["_id"] = str(doc["_id"])
        actions.append(doc)

    out_file = approvals_dir / "pending_actions.json"
    out_file.write_text(json.dumps(actions, indent=2, default=str))
    print(f"  ✓ Exported {len(actions)} approval records")
    return actions


async def export_metrics(output_dir: Path):
    """Load eval results if they exist."""
    metrics_dir = output_dir / "metrics"
    metrics_dir.mkdir(exist_ok=True)

    eval_results_path = Path("evaluation_results.json")
    if eval_results_path.exists():
        content = eval_results_path.read_text()
        (metrics_dir / "eval_summary.json").write_text(content)
        data = json.loads(content)
        print(f"  ✓ Exported eval results: {len(data.get('scenarios', []))} scenarios")
        return data
    else:
        placeholder = {
            "note": "Run run_phase3_evals.py to generate evaluation scores before submission.",
            "expected_fields": ["scenario_id", "score", "pass", "notes"]
        }
        (metrics_dir / "eval_summary.json").write_text(json.dumps(placeholder, indent=2))
        print("  ⚠️  No eval results found — placeholder written. Run evaluations first!")
        return placeholder


def write_readme(output_dir: Path, sessions_summary: list, actions_count: int):
    readme = f"""# PantryMind — Hackathon Submission Evidence
## Google Cloud Agent Builder + MongoDB MCP Track

Generated: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

---

## What Is PantryMind?

PantryMind is a multi-agent personal AI life management system built with Google ADK.
It manages household inventory, receipts, meal planning, and financial tracking using
a governed agent hierarchy backed by MongoDB Atlas via the **official MongoDB MCP server**.

---

## Track Requirements Met

| Requirement | Implementation |
|---|---|
| Google Cloud Agent Builder | Google ADK with `Runner` + `LlmAgent` hierarchy |
| MongoDB MCP Integration | `@mongodb-js/mcp-server-mongodb` via `StdioServerParameters` |
| Multi-Agent Architecture | 1 orchestrator + 5 specialized sub-agents |
| Streaming Response | SSE endpoint (`/api/agent/chat`) with live token streaming |
| Human-in-the-Loop | Governance layer with approval inbox UI |

---

## Evidence Files

### traces/
- **{len(sessions_summary)} session traces** captured from MongoDB `agent_traces` collection
- Each file contains the full ordered event log for one conversation
- Events include: session_start, agent_transfer, tool_call, mcp_query, approval_required, final_response

### approvals/
- **{actions_count} governance records** from MongoDB `pending_actions` collection
- Demonstrates the human-in-the-loop approval layer
- Shows risk_level classification and approve/reject workflow

### metrics/
- Evaluation scores from the Phase 3 evaluation harness
- Scenarios cover: pantry query, meal plan, receipt scan, budget analysis, shopping list

---

## Architecture

See `architecture.json` for the full agent hierarchy and tool mapping.

---

## Key Files To Review

| File | Purpose |
|---|---|
| `adk/orchestrator.py` | Root orchestrator — plan-then-execute routing |
| `adk/mcp/mongodb_mcp.py` | Official MongoDB MCP toolset (read-only + governed writes) |
| `adk/governance/action_policy.py` | Human-in-the-loop policy engine |
| `adk/demo/evidence_logger.py` | Structured trace logging |
| `routers/agent.py` | SSE streaming endpoint |
| `frontend/src/components/ApprovalInbox.jsx` | Approval UI |
| `frontend/src/components/TraceTimeline.jsx` | Trace visualization UI |
"""
    (output_dir / "README.md").write_text(readme)
    print("  ✓ README.md written")


async def run_sanity_check():
    """Quick smoke-test against the running server."""
    import urllib.request
    try:
        with urllib.request.urlopen("http://localhost:8000/health", timeout=3) as resp:
            data = json.loads(resp.read())
            status = data.get("status")
            print(f"\n  🟢 Server health: {status} | DB: {data.get('database')}")
            return True
    except Exception as e:
        print(f"\n  🔴 Server not reachable: {e}")
        return False


async def main(sanity_check: bool = False):
    uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGODB_DATABASE", "finmind")
    
    if not uri:
        print("❌ MONGODB_URI not set in .env")
        sys.exit(1)

    print(f"\n📦 Exporting submission evidence to ./{OUTPUT_DIR}/")
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Connect to MongoDB
    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=10000, tlsCAFile=certifi.where())
    db = client[db_name]
    print(f"  ✓ Connected to MongoDB: {db_name}")

    # Write architecture manifest
    arch_file = OUTPUT_DIR / "architecture.json"
    arch_file.write_text(json.dumps(ARCHITECTURE, indent=2))
    print("  ✓ architecture.json written")

    # Export traces
    print("\n📝 Exporting agent traces...")
    sessions_summary = await export_traces(db, OUTPUT_DIR)

    # Export approvals
    print("\n🛡️  Exporting governance records...")
    actions = await export_approvals(db, OUTPUT_DIR)

    # Export metrics
    print("\n📊 Exporting evaluation metrics...")
    await export_metrics(OUTPUT_DIR)

    # Write README
    print("\n📄 Writing README...")
    write_readme(OUTPUT_DIR, sessions_summary, len(actions))

    # Screenshots placeholder
    (OUTPUT_DIR / "screenshots").mkdir(exist_ok=True)
    (OUTPUT_DIR / "screenshots" / "README.txt").write_text(
        "Add demo video screenshots or screen recordings here before submission.\n"
    )

    client.close()

    if sanity_check:
        print("\n🔍 Running sanity check against running server...")
        await run_sanity_check()

    print(f"\n✅ Evidence package ready at: {OUTPUT_DIR.resolve()}")
    print("   Next step: Review README.md and run evaluations with run_phase3_evals.py\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export PantryMind submission evidence")
    parser.add_argument("--sanity-check", action="store_true", help="Ping the running server too")
    args = parser.parse_args()
    asyncio.run(main(sanity_check=args.sanity_check))
