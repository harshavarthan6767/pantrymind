import os
import vertexai
from google.cloud import aiplatform

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

def init_vertex():
    if PROJECT_ID:
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        aiplatform.init(project=PROJECT_ID, location=LOCATION)
    else:
        print("WARNING: GOOGLE_CLOUD_PROJECT not set, Vertex AI not initialized.")
