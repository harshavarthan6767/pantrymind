# 🛒 PantryMind - AI Pantry Manager & Receipt Scanner

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)
[![Built with Gemini](https://img.shields.io/badge/Built%20with-Gemini-blueviolet)](https://ai.google.dev/)
[![MongoDB MCP](https://img.shields.io/badge/MongoDB-MCP-brightgreen)](https://www.mongodb.com/)

PantryMind is an intelligent grocery inventory management application built to automate receipt scanning and tracking. It uses a modern **Multi-Agent Architecture** powered by Google ADK, Gemini 2.5 Flash, and the official MongoDB MCP server to manage household inventory, receipts, meal planning, and finances.

---

## 🚀 Key Features & Differentiators

1. **Official MongoDB MCP Integration**: Database interactions are powered by `@mongodb-js/mcp-server-mongodb` using npx. This isn't a wrapper—it's native MCP standard bridging AI and Atlas.
2. **Multi-Agent Orchestration (Google ADK)**: Separate specialized agents handle the Kitchen, Finances, Pantry, and Shopping, managed by a smart Orchestrator.
3. **Human-in-the-Loop Governance**: A robust policy engine intercepts potentially destructive actions (e.g., adding/deleting inventory). An Approval Inbox UI forces user sign-off for medium/high-risk actions.
4. **Agent Reflexion**: The Kitchen Agent self-critiques its generated meal plans against your dietary constraints and expiring items before showing them to you.
5. **Atlas Vector Search**: Semantic pantry queries allow you to ask for "Thai curry ingredients" instead of strict exact-match searches.
6. **Pure Client-Side OCR**: Uses HTML5 Canvas + WebAssembly (Tesseract.js) in a Web Worker to parse receipts directly in the browser without backend CPU freezing.

---

## 🏛 Architecture Overview

The application is split into a **Vite + React Frontend** and a **FastAPI + MongoDB Backend**.

### 1. The Multi-Agent Layer
- **Orchestrator**: Evaluates user queries and routes them to the correct sub-agent.
- **Pantry Agent**: Has governed write-access to the inventory collection.
- **Finance Agent**: Read-only access to the financial ledger for spending summaries.
- **Kitchen Chef**: Read-only access; runs the PuLP optimizer to balance macros and Reflexion to double-check meal plans.

### 2. The Lightweight Client-Side OCR Architecture
Instead of heavy server-side processing, OCR runs in-browser using **HTML5 Canvas Preprocessing** (grayscale/contrast filters) and **Tesseract.js (Web Workers)**. Raw OCR output is processed by a resilient "Bouncer & Chopper" parsing engine that eliminates junk characters, isolates prices, and formats a clean JSON payload.

### 3. The Backend API
- **Framework**: FastAPI with asynchronous endpoints.
- **Database**: MongoDB (via `motor.motor_asyncio`) storing data in `inventory`, `receipts`, and `financial_ledger`.

---

## 📂 Directory Structure

### `/frontend` (React + Vite)
- `src/components/`: UI components including `Dashboard.jsx`, `InventoryList.jsx`, `GlobalVoiceAgent.jsx`, and `ApprovalInbox.jsx`.
- `src/services/`: 
  - `ocrService.js`: Client-side OCR parsing logic.
  - `api.js`: Axios wrapper for communicating with the FastAPI backend.

### `/` (Root Backend)
- `main.py`: FastAPI application routing.
- `adk/`: Agent Development Kit definitions for the orchestrator and specialized agents.
- `services/`: Motor async client, Voice WebSocket service, Kitchen service.
- `tools/`: MCP and custom tools for the agents.

---

## 💻 Setup & Execution

### 1. Prerequisites
- **Node.js** (v18+ recommended)
- **Python** (v3.10+ recommended)
- **MongoDB Atlas** account (M0 free tier is fine)
- **Google Cloud Platform / Gemini API Key**

### 2. Environment Variables
Create a `.env` file in the root:
```env
MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.mongodb.net/finmind?retryWrites=true&w=majority
MONGODB_DATABASE=finmind
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GEMINI_API_KEY=your_api_key
GEMINI_MODEL=gemini-2.5-flash
VOICE_DISABLE_TOOLS=false
```

### 3. Backend Setup
```bash
python -m venv .venv
.\.venv\Scripts\activate  # Windows
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

The application will be available at `http://localhost:5173`.

---

## 🏆 Hackathon Submission
This project is submitted to the **Google Cloud Agent Builder + MongoDB MCP** track.
* **Demo Video**: [Coming Soon](https://youtube.com)
* **Evidence Package**: Included in the `submission_evidence` folder.
* **Live Demo**: *PantryMind is an Electron desktop app.* To run it locally, please follow the setup instructions above or use the provided `StartPantryMind.bat` script on Windows.

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
