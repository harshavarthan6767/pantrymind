# -----------------------------------------------------------------------------
# PantryMind — Vertex AI Agent Engine Deployment Script (Hackathon Phase 1)
# -----------------------------------------------------------------------------

# Requirements:
# 1. Google Cloud CLI installed and authenticated
# 2. Project configured with Vertex AI API enabled

$PROJECT_ID = "YOUR_GOOGLE_CLOUD_PROJECT_ID"
$REGION = "us-central1"
$APP_NAME = "pantrymind"
$IMAGE_URI = "gcr.io/$PROJECT_ID/$APP_NAME:latest"

Write-Host "Deploying PantryMind to Google Cloud / Vertex AI Agent Engine..." -ForegroundColor Cyan

# 1. Build and submit Docker image to Container Registry
Write-Host "1. Building container image..."
gcloud builds submit --tag $IMAGE_URI

# 2. Deploy to Cloud Run (Vertex AI Agent Engine backend)
Write-Host "2. Deploying to Cloud Run..."
gcloud run deploy $APP_NAME `
    --image $IMAGE_URI `
    --region $REGION `
    --allow-unauthenticated `
    --set-env-vars="APP_ENV=production,GEMINI_API_KEY=YOUR_API_KEY,MONGODB_URI=YOUR_MONGO_URI"

Write-Host "Deployment complete! Your agent API is live." -ForegroundColor Green
Write-Host "Make sure to update your frontend VITE_API_URL to point to the Cloud Run URL."
