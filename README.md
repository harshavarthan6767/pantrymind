# 🛒 PantryMind - AI Pantry Manager & Receipt Scanner

PantryMind is an intelligent inventory management web application built with a modern React (Vite) frontend and a FastAPI backend. It features an advanced **Offline Receipt OCR Agent** that can scan grocery receipts and automatically extract items, prices, and quantities to keep your pantry inventory up to date!

## ✨ Features
- **Advanced Offline OCR:** Uses PaddleOCR and OpenCV to read messy receipts completely offline.
- **AI Layout Parsing:** Intelligently figures out which prices belong to which items and calculates quantities.
- **Pantry Inventory Tracking:** Add, remove, edit, and keep track of expiring items.
- **Financial & Nutrition Analytics:** Track monthly grocery spending and basic item insights.
- **Responsive Dashboard:** A beautiful, animated UI powered by React and TailwindCSS.

## 🛠 Tech Stack
- **Frontend:** React 18, Vite, TailwindCSS, Lucide Icons, Recharts
- **Backend:** Python 3.10+, FastAPI, Uvicorn
- **Database:** MongoDB (Motor Asyncio)
- **AI/ML:** PaddleOCR, PaddlePaddle, OpenCV (Headless)

---

## 🚀 Setup & Installation

### 1. Prerequisites
- **Node.js** (v18+ recommended)
- **Python** (v3.10+ recommended)
- **MongoDB Atlas** account (or local MongoDB server)

### 2. Clone the Repository
```bash
git clone https://github.com/your-username/pantrymind.git
cd pantrymind
```

### 3. Environment Variables
Create a `.env` file in the root of the project:
```env
# MongoDB Connection String (Replace with your actual cluster URI)
MONGO_URI=mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority
```

### 4. Backend Setup
The backend handles the API and the intensive ML receipt scanning pipeline.

```bash
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# On Windows:
.\.venv\Scripts\activate
# On Mac/Linux:
source .venv/bin/activate

# Install all backend dependencies
pip install -r requirements.txt
```

### 5. Frontend Setup
The frontend is a Vite + React application.

```bash
# Install Node dependencies
npm install
```

---

## 🏃‍♂️ Running the Application

You will need two terminal windows to run both the frontend and backend simultaneously.

**Terminal 1: Start the Backend (FastAPI)**
```bash
# Ensure your virtual environment is active, then run:
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```
*Note: The first time you upload a receipt, PaddleOCR may take a moment to download its inference models.*

**Terminal 2: Start the Frontend (Vite)**
```bash
npm run dev
```

The application will be available at `http://localhost:5173`.

---

## 🧠 Architecture Overview
The OCR Pipeline works across several distinct phases when a receipt is uploaded:
1. **Image Preprocessing:** OpenCV converts the image to grayscale and applies adaptive thresholding to remove shadows.
2. **Text Detection:** PaddleOCR scans the image and detects bounding boxes for all text.
3. **Spatial Grouping:** The parser groups bounding boxes by their Y-coordinates to form distinct rows.
4. **Entity Extraction:** Regular expressions identify prices, quantities, and item names from the grouped rows.
5. **Validation:** The final total is checked against the sum of the extracted items before saving to MongoDB.
