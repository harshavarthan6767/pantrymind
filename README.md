# 🛒 PantryMind - AI Pantry Manager & Receipt Scanner

PantryMind is an intelligent grocery inventory management application built to automate receipt scanning and tracking. It uses a modern **client-side OCR architecture** to parse physical receipts directly in the browser, completely eliminating the need for heavy server-side machine learning dependencies!

---

## 🏛 Architecture Overview

The application is split into a **Vite + React Frontend** and a **FastAPI + MongoDB Backend**.

### 1. The Lightweight Client-Side OCR Architecture
Initially, the project used server-side Python libraries (PaddleOCR, OpenCV, ONNX) to process receipts. This was completely overhauled to a **Pure WebAssembly (WASM)** architecture for maximum scalability.

- **HTML5 Canvas Preprocessing**: Instead of using Python's OpenCV, the frontend uses native `canvas.getContext('2d')` to instantly scale down high-resolution smartphone photos and apply `grayscale` and `contrast` filters before scanning. This prevents browser CPU freezing.
- **Tesseract.js (Web Workers)**: The preprocessed image is passed to `Tesseract.js`, a WASM port of the famous OCR engine. By running in a background Web Worker thread, it extracts text asynchronously without interrupting the React UI animations.

### 2. The "Bouncer & Chopper" Parsing Engine
Raw OCR output from receipts is notoriously messy (often called "OCR garbage"). We implemented a highly resilient, subtractive JavaScript parsing loop in `frontend/src/services/ocrService.js`:

- **The Bouncer**: Instantly rejects lines containing structural metadata (e.g., "SUBTOTAL", "TAX", "TOTAL").
- **The Chopper**: Chops off any internal categorization metadata that might have been appended by other systems.
- **The Junk Filter**: Evaluates the ratio of symbols (like `—`, `=`, `~`) to alphanumeric characters. If a line is heavily skewed towards symbols, it is classified as a "phantom line" (a crease or shadow hallucination) and silently dropped.
- **Subtractive Price Extraction**: To defeat the "Double-Price Trap" (where receipts print Unit Price and Total Price on the same line), the parser globally extracts *all* decimals first, assigns the final one to the total, and then completely erases them from the string.
- **Cleanup**: Weights, quantities, and trailing tax flags (`F` or `T`) are individually regex-matched and wiped out.
- **Final Polish**: What remains is a pristine item name, completely stripped of all numbers, weights, and symbols.

### 3. The Backend API
The backend (`main.py`) acts as a fast, asynchronous persistence layer.
- **Framework**: FastAPI with asynchronous endpoints.
- **Database**: MongoDB (via `motor.motor_asyncio`), storing data in specific collections: `inventory`, `receipts`, `financial_ledger`, etc.
- **Data Flow**: The frontend sends a clean JSON payload (`ReceiptData` Pydantic model) containing the extracted items and total. The backend iterates through the array, inserting items into the `inventory` collection and appending a transaction to the `financial_ledger`.

---

## 📂 Directory Structure

### `/frontend` (React + Vite)
- `src/components/`: Contains UI components like `Dashboard.jsx` (main view), `InventoryList.jsx`, and `ScanReceiptModal.jsx` (handles file upload UI).
- `src/services/`: 
  - `ocrService.js`: The heart of the client-side OCR. Handles Canvas preprocessing, Tesseract extraction, and the Chopper/Bouncer logic.
  - `api.js`: Axios wrapper for communicating with the FastAPI backend.

### `/` (Root Backend)
- `main.py`: The FastAPI application. Defines Pydantic models (e.g., `InventoryItem`, `ReceiptData`) and contains all routing (`/api/inventory`, `/api/receipts/upload`).
- `services/mongodb.py`: The asynchronous Motor client wrapper to handle generic CRUD operations across the various MongoDB collections.
- `requirements.txt`: Python dependencies (FastAPI, Motor, Uvicorn, Pydantic).

---

## 🚀 Setup & Execution

### 1. Prerequisites
- **Node.js** (v18+ recommended)
- **Python** (v3.10+ recommended)
- **MongoDB Atlas** account (or local MongoDB server)

### 2. Environment Variables
Create a `.env` file in the root of the project:
```env
MONGO_URI=mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority
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
