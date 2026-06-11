# PantryMind — Hackathon Submission Checklist
## Google Cloud Agent Builder + MongoDB MCP Track

> Run this checklist top-to-bottom on the day of submission.

---

## ✅ Pre-Demo Environment

- [ ] `.env` file contains `MONGODB_URI`, `GEMINI_API_KEY` / `GOOGLE_CLOUD_PROJECT`
- [ ] Node.js installed (`node --version` shows v18+)
- [ ] `@mongodb-js/mcp-server-mongodb` accessible via npx
- [ ] Python venv active (`.venv\Scripts\activate`)
- [ ] All dependencies installed (`pip install -r requirements.txt`)

---

## ✅ Database

- [ ] MongoDB Atlas cluster is running (M0 free tier is fine)
- [ ] Atlas Vector Search index named `pantry_semantic` is enabled on `inventory.embedding`
- [ ] Demo data seeded: `.venv\Scripts\python seed_phase3_demo_data.py --clear`
- [ ] Verify data in Atlas UI or via `mongosh`

---

## ✅ Server

- [ ] Start backend: `.venv\Scripts\uvicorn main:app --reload --port 8000`
- [ ] Check health: `curl http://localhost:8000/health` → `{"status":"healthy","database":"connected"}`
- [ ] MCP health check: `.venv\Scripts\python mcp_healthcheck.py`
- [ ] Start frontend: `cd frontend && npm run dev` → Vite running at `http://localhost:5173`

---

## ✅ Phase 3 Features to Demo

### 1. Multi-Agent Routing (Google ADK)
- [ ] Open chat → ask "What ingredients do I have for a Thai curry?"
- [ ] Watch Trace Timeline show: `session_start` → `agent_transfer → pantry_agent` → `tool_call: semantic_pantry_search`
- [ ] Copy the `session_id` from UI

### 2. MongoDB MCP Integration
- [ ] Ask "What's expiring in my pantry?"
- [ ] Watch `tool_call: find` in trace → pantry_agent queries `inventory` via MCP
- [ ] Show in Atlas that the correct documents exist

### 3. Human-in-the-Loop (Governance)
- [ ] Ask "Add 2 kg of chicken to my inventory"
- [ ] Approval Inbox appears (bottom-right) with ⚠️ MEDIUM RISK badge
- [ ] Click **Approve** → item executes
- [ ] Ask "Delete all my expired items" → should be BLOCKED by policy

### 4. Trace Timeline
- [ ] Navigate to Settings or open a trace panel showing the session from step 1
- [ ] Show event count, agent transfers, tool calls, and approval events

### 5. Meal Plan + Reflexion
- [ ] Ask "Plan dinner using what's about to expire"
- [ ] Kitchen agent prioritizes salmon + spinach (expiring items)
- [ ] Reflexion step modifies/validates the draft plan

---

## ✅ Evidence Package

- [ ] Run evals: `.venv\Scripts\python run_phase3_evals.py --verbose`
- [ ] Export evidence: `.venv\Scripts\python export_submission_evidence.py --sanity-check`
- [ ] Review `submission_evidence/README.md`
- [ ] Upload `submission_evidence/` folder to Google Drive / GitHub

---

## ✅ Final Submission

- [ ] GitHub repo is public
- [ ] `README.md` at repo root links to demo video
- [ ] `submission_evidence/` folder committed
- [ ] Demo video (2-3 min) uploaded and link in README
- [ ] Track form submitted: Google Cloud Agent Builder + MongoDB MCP

---

## 🎯 Key Differentiators to Highlight

1. **Official MongoDB MCP** — not a wrapper, actual `@mongodb-js/mcp-server-mongodb` via npx
2. **Read-only / write-governed split** — kitchen, finance, shopping = read-only; pantry, receipt = governed writes
3. **Human-in-the-Loop** — policy engine with risk levels, real approval UI, audit trail in MongoDB
4. **Evidence Tracing** — every event logged to `agent_traces` collection, browsable in frontend
5. **Reflexion** — kitchen + finance agents self-critique before returning to user
6. **Atlas Vector Search** — semantic pantry queries (Thai curry, breakfast ingredients, etc.)
