# PantryMind
> AI-powered multi-agent life management with voice, governance, and real-time inventory intelligence

## 🔗 Links
- **Live Demo:** https://harshavarthan6767.github.io/pantrymind/demo-video/index.html
- **Repo:** https://github.com/harshavarthan6767/pantrymind
- **Devpost:** [Link to your Devpost Submission]

## 📖 About
PantryMind is an intelligent multi-agent system built on Google ADK and powered by the official MongoDB MCP server. It transforms household management by automating grocery tracking, smart recipe generation, and financial ledgers, all protected by a strict Human-in-the-Loop safety system.

## 🚀 Features
- **Official MongoDB MCP Integration:** Direct database interactions powered by `@mongodb-js/mcp-server-mongodb`.
- **Multi-Agent Orchestration:** Specialized agents (Kitchen, Finance, Pantry, Shopping) managed by a central Orchestrator.
- **Human-in-the-Loop Governance:** Approval Inbox UI intercepts potentially destructive database actions.
- **Agent Reflexion:** The Kitchen Agent self-critiques meal plans against dietary constraints before suggesting them.
- **Atlas Vector Search:** Semantic pantry queries ("Thai curry ingredients") using high-dimensional embeddings.
- **Client-Side OCR:** Parse receipts directly in the browser via HTML5 Canvas + WebAssembly.

## 🛠 Tech Stack
- Google ADK (Agent Development Kit)
- Gemini 3.1 Pro & Gemini Live
- MongoDB Atlas & Vector Search
- Official MongoDB MCP Server
- React / Vite
- FastAPI / Python

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

## 📄 License
MIT © Harshavarthan 2026
