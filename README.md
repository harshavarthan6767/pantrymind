<div align="center">
  <img src="https://raw.githubusercontent.com/harshavarthan6767/pantrymind/main/frontend/public/icon.png" alt="PantryMind Logo" width="120" />

  # PantryMind

  **AI-powered multi-agent life management with voice, governance, and real-time inventory intelligence**

  [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
  [![Vercel](https://img.shields.io/badge/Deployed-Vercel-black.svg)](https://harshavarthan6767.github.io/pantrymind/)
  [![Gemini](https://img.shields.io/badge/Powered_by-Gemini_3.1_Pro-8A2BE2.svg)](https://deepmind.google/technologies/gemini/)

  [Live UI Demo](https://harshavarthan6767.github.io/pantrymind/) • [Architecture Details](docs/VOICE_AGENT_ARCHITECTURE.md) • [Devpost Submission](https://devpost.com/software/pantrymind)
</div>

<br/>

## 🎥 Watch the Demo

[![PantryMind Demo Video](https://img.youtube.com/vi/eOzJ_bl4azM/maxresdefault.jpg)](https://youtu.be/eOzJ_bl4azM)

*(Click the image above to watch our full project showcase on YouTube)*

---

## 📖 Inspiration
Managing a household is effectively a multi-dimensional optimization problem. Traditional inventory apps fail because they require tedious manual data entry and offer static, rigid queries. 

I was inspired to build an intelligent system that doesn't just passively store data, but actively manages your household using autonomous reasoning. I wanted an AI that could scan a receipt, categorize the items, understand nutritional constraints, track your financial ledger, and converse with you over voice—all while ensuring that it could never accidentally delete your data without your permission.

---

## ⚙️ How It Works (The Multi-Agent Architecture)
PantryMind uses a **Multi-Agent Architecture** running on **Google ADK (Agent Development Kit)** and **Gemini 3.1 Pro** to manage your kitchen and finances through natural language. 

- **Voice-First Input**: You can literally speak to the system: *"What ingredients do I have for a Thai curry?"*
- **Semantic Pantry Search (Atlas Vector Search)**: It retrieves exact and semantically similar ingredients from your inventory using Cosine Similarity matching.
- **Automated Meal Planning**: The Kitchen Chef agent checks expiring items and generates macro-optimized recipes on the fly.
- **Reflexion Engine**: Before showing a meal plan to the user, the agent evaluates its own draft against a strict set of user dietary constraints and macro goals, recalculating its output if constraints are violated.

### 🛟 Human-in-the-Loop Governance
To bridge the AI reasoning with the database, we integrated the **official MongoDB MCP Server**. 

Because LLMs can hallucinate, we built a Human-in-the-Loop policy engine. Before any agent can modify your core database (like restocking inventory or deleting items), the action is intercepted by an **Approval Inbox**. You must explicitly approve medium/high-risk actions via the UI before the transaction commits.

---

## 🚀 Key Features
- **Official MongoDB MCP Integration:** Direct database interactions powered by `@mongodb-js/mcp-server-mongodb`.
- **Dual-Signal Voice Safety Net:** Solves voice UI latency and ASR (Automatic Speech Recognition) errors by forcing reliable agent fallbacks even when transcripts are garbled.
- **Client-Side WASM OCR:** Parse physical receipts directly in the browser via HTML5 Canvas + WebAssembly, without sending images to a backend server.
- **Finance & Ledger Management:** Specialized agents track your spending automatically as receipts are scanned.

---

## 🛠 Tech Stack
* **Agent Engine**: Google ADK, Gemini 3.1 Pro, Gemini Live
* **Database & Search**: MongoDB Atlas, Atlas Vector Search
* **Database Protocol**: Official MongoDB MCP Server (`@mongodb-js/mcp-server-mongodb`)
* **Backend**: Python, FastAPI
* **Frontend**: React, Vite, TailwindCSS
* **Vision/OCR**: Pure Client-side WebAssembly + HTML5 Canvas

---

## ⚙️ Setup & Run Locally

```bash
git clone https://github.com/harshavarthan6767/pantrymind.git
cd pantrymind

# 1. Backend Setup
python -m venv .venv
.\.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Start FastAPI server
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 2. Frontend Setup (in a new terminal)
cd frontend
npm install
npm run dev
```

> **Note on Live Links**: The Vercel deployment acts as a UI showcase. Because the actual AI brain runs a local Python backend and local MCP server, full capabilities (Voice, Agents, Database) require running the project locally as shown above.

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
