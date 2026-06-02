# ============================================================
# PantryMind — Multi-stage Docker Build
# Stage 1: Build React frontend
# Stage 2: Python + FastAPI serving the built frontend
# ============================================================

# ---- Stage 1: Frontend Build ----
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --production=false
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python API + Static Files ----
FROM python:3.13-slim AS runtime
WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY main.py .
COPY agents/ agents/
COPY services/ services/
COPY tools/ tools/
COPY data/ data/

# Copy built frontend into static/
COPY --from=frontend-build /app/frontend/dist ./static

# Expose port
ENV PORT=8080
EXPOSE 8080

# Run with uvicorn
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
