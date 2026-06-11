# PantryMind — Demo Video Script
## Google Cloud Agent Builder + MongoDB MCP Track · 3-Minute Version

---

## 🎬 SCENE 1: Intro (0:00 – 0:20)

**[Screen: PantryMind dashboard open in browser]**

> "Hi, I'm Harsh. This is PantryMind — a multi-agent AI life management system
> built with Google ADK, Gemini 3.1 Pro, and the official MongoDB MCP server.
> PantryMind manages household inventory, receipts, meal planning, and finances —
> all through natural language, with a governed human-in-the-loop layer."

---

## 🎬 SCENE 2: Multi-Agent Chat (0:20 – 0:50)

**[Open chat, type message]**

> "Let me show you the agent working. I'll ask about Thai curry ingredients."

**Type:** `"What ingredients do I have that would work for a Thai curry?"`

**[Point to left panel showing agent activity]**

> "Watch the live agent trace — the Orchestrator routes to the Pantry Agent,
> which calls semantic_pantry_search using Atlas Vector Search...
> and here are the matching items: coconut milk, green curry paste, jasmine rice."

---

## 🎬 SCENE 3: MongoDB MCP in Action (0:50 – 1:20)

**[Point to trace timeline]**

> "Every tool call goes through the official @mongodb-js/mcp-server-mongodb.
> This is not a wrapper — it's the real MCP server launched via npx, communicating
> over stdio with our ADK runner."

**[Show trace: mcp_query event with collection='inventory']**

> "You can see the exact MCP query here — find in the inventory collection.
> The data comes back through MongoDB Atlas and is summarized by Gemini."

---

## 🎬 SCENE 4: Governance — Approval Gate (1:20 – 1:50)

**Type:** `"Add 2 kg of chicken to my pantry"`

**[Approval Inbox pops up in bottom-right corner]**

> "Phase 3's key feature — Human-in-the-Loop governance.
> The receipt_agent wants to insert a document into inventory.
> Our policy engine flags this as MEDIUM RISK and creates a pending action
> instead of committing immediately."

**[Click Approve]**

> "I approve — and only now does the executor replay the agent's intent and
> insert the document into MongoDB. Every action is audited in the agent_traces
> collection."

---

## 🎬 SCENE 5: Meal Plan + Reflexion (1:50 – 2:20)

**Type:** `"Plan tonight's dinner using items that are about to expire"`

> "The Kitchen Chef agent checks for expiring items first — salmon and spinach.
> It runs the PuLP meal optimizer to balance macros, then...
> critically, it calls finalize_meal_plan() which is our Reflexion step.
> Gemini re-reads the draft and fixes quantity errors or dietary violations."

**[Show response with expiry warning emoji and nutrition summary]**

---

## 🎬 SCENE 6: Finance + Shopping (2:20 – 2:50)

**Type:** `"How much have I spent on groceries this month?"`

> "Finance agent — read-only, never writes. It aggregates the financial_ledger
> collection via MCP and returns the answer in ₹."

**Type:** `"Generate my shopping list for this week, under ₹2000"`

> "Shopping agent generates a prioritized list — P1 must-buys within budget."

---

## 🎬 SCENE 7: Wrap-Up (2:50 – 3:00)

**[Show architecture diagram or code briefly]**

> "PantryMind: Google ADK · Gemini 3.1 Pro · MongoDB Atlas + Official MCP Server
> · Human-in-the-Loop governance · Atlas Vector Search · Reflexion.
> Thank you."

---

## 📋 Recording Tips

- Record at 1920×1080, 30fps
- Use OBS or Loom for screen recording
- Keep browser zoom at 100%
- Disable notifications before recording
- Upload to YouTube (unlisted) and link in README
