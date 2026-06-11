# PantryMind - Devpost Submission

## Project Name
PantryMind

## Tagline
AI-powered multi-agent life management with voice, governance, and real-time inventory intelligence

## Elevator Pitch
PantryMind is a multi-agent life manager powered by Google ADK & MongoDB MCP. It handles groceries, meal planning & finances via voice, protected by a Human-in-the-Loop safety system.

---

## 📖 Inspiration
Managing a household is effectively a multi-dimensional optimization problem. People buy groceries, forget what they have, throw out expired food, and struggle daily to figure out what to cook with the ingredients that remain. Traditional inventory apps fail because they require tedious manual data entry and offer static, rigid queries. 

I was inspired to build an intelligent system that doesn't just passively store data, but actively manages your household using autonomous reasoning. I wanted an AI that could scan a receipt, categorize the items, understand nutritional constraints, track your financial ledger, and converse with you over voice—all while ensuring that it could never accidentally delete your data without your permission.

## ⚙️ What it does
PantryMind uses a **Multi-Agent Architecture** to manage your kitchen and finances through natural language. 
- **Voice-First Input**: You can literally speak to the system: *"What ingredients do I have for a Thai curry?"*
- **Semantic Pantry Search**: It retrieves exact and semantically similar ingredients from your inventory.
- **Automated Meal Planning**: The Kitchen Chef agent checks expiring items and generates macro-optimized recipes on the fly.
- **Human-in-the-Loop Governance**: Before any agent can modify your core database (like restocking inventory or deleting items), the action is intercepted by an Approval Inbox. You must explicitly approve medium/high-risk actions before the transaction commits.

## 🛠 How we built it
The core engine runs on **Google ADK (Agent Development Kit)** orchestrating **Gemini 3.1 Pro** models. Each aspect of the house is governed by a specialized sub-agent (Pantry Agent, Finance Agent, Kitchen Chef, Shopping Agent).

To bridge the AI reasoning with the database, we integrated the **official MongoDB MCP (Model Context Protocol) Server**. Instead of writing custom middleman APIs, our agents communicate directly with MongoDB via the standardized MCP protocol over `stdio`.

For the semantic search, we leverage **MongoDB Atlas Vector Search**. When a user asks for "Thai curry ingredients", the system embeds the query into a high-dimensional vector $Q$ and compares it against inventory item embeddings $V_i$ using Cosine Similarity to find relevant, non-exact matches:

$$ S_C(Q, V_i) = \frac{Q \cdot V_i}{\|Q\| \|V_i\|} $$

Furthermore, the **Kitchen Chef Agent** uses a **Reflexion** pattern. Before showing a meal plan to the user, the agent evaluates its own draft against a strict set of user dietary constraints and macro goals, recalculating its output if constraints are violated.

## 🧗 Challenges we ran into
Integrating the official MongoDB MCP Server natively with Google ADK agents required careful schema mapping to ensure the LLM's generated `tool_calls` perfectly matched the MCP protocol requirements for complex database operations.

Another significant challenge was **Voice UI Latency**. Relying solely on audio transcriptions often resulted in truncated or misunderstood commands (e.g., transcribing "make me a meal" as "mir ja"). We had to implement a dual-signal "Safety Net" that analyzes both the input transcript and the AI's generated output text to reliably trigger the correct agent hand-offs.

## 🏆 Accomplishments that we're proud of
- Successfully integrating the **official `@mongodb-js/mcp-server-mongodb`** directly via `npx`, avoiding custom wrappers and proving the power of the MCP standard.
- Building a robust **Human-in-the-Loop policy engine** that intercepts destructive database intents and forces a physical UI approval gate before committing.
- Achieving **Pure Client-Side WebAssembly OCR**. Instead of heavy backend servers, physical receipts are processed entirely in the browser using HTML5 Canvas preprocessing and Tesseract.js running on background Web Workers.

## 🧠 What we learned
We learned the sheer power of isolating AI responsibilities. By explicitly giving the Finance Agent "read-only" access while giving the Pantry Agent "governed write-access", we dramatically reduced AI hallucinations and destructive behaviors. We also learned that providing an LLM direct database access via MCP is incredibly powerful, but *requires* an approval layer for real-world safety.

## 🚀 What's next for PantryMind
- **Supermarket API Integration**: Allowing the Shopping Agent to autonomously place orders for missing ingredients when a recipe is requested.
- **Dietary Expansion**: Enhancing the Reflexion engine to support highly specialized medical diets (e.g., low-FODMAP, renal diets).
- **Mobile Companion**: Moving the WebAssembly OCR engine to a native mobile companion app for instantly scanning receipts on the go.

## 💻 Built With
- `google-adk`
- `gemini-3.1-pro`
- `mongodb-atlas`
- `mcp` (Model Context Protocol)
- `fastapi`
- `react` / `vite`
- `electron`
