"""
Google Cloud Storage Tools for PantryMind.

Upload and retrieve receipt/invoice images to/from a GCS bucket.
"""

import os
import logging

from google.adk.tools import ToolContext
from google.cloud import storage

logger = logging.getLogger("pantrymind.tools.storage")

_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "pantrymind-receipts")
_gcs_client: storage.Client | None = None


def _get_client() -> storage.Client:
    """Lazily initialise the GCS client."""
    global _gcs_client
    if _gcs_client is None:
        _gcs_client = storage.Client()
    return _gcs_client


async def store_receipt_image(
    image_bytes: bytes,
    filename: str,
    tool_context: ToolContext,
) -> str:
    """Upload a receipt or invoice image to Google Cloud Storage.

    Call this tool when you need to persist a receipt/invoice image for
    future reference. Returns the GCS URI (gs://bucket/path) that can
    be stored alongside the receipt record in MongoDB.

    Args:
        image_bytes: Raw bytes of the image file.
        filename: Desired filename (e.g. 'receipt_2026-06-01_bigbazaar.jpg').
        tool_context: ADK tool context for session state access.

    Returns:
        str — the GCS URI of the uploaded file (e.g. gs://bucket/receipts/filename).
    """
    try:
        client = _get_client()
        bucket = client.bucket(_BUCKET_NAME)
        blob_path = f"receipts/{filename}"
        blob = bucket.blob(blob_path)

        # Infer content type from extension
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpeg"
        content_type_map = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp",
            "pdf": "application/pdf",
            "tiff": "image/tiff",
            "tif": "image/tiff",
        }
        content_type = content_type_map.get(ext, "application/octet-stream")

        blob.upload_from_string(image_bytes, content_type=content_type)
        gcs_uri = f"gs://{_BUCKET_NAME}/{blob_path}"

        logger.info("Uploaded %d bytes to %s", len(image_bytes), gcs_uri)
        return gcs_uri

    except Exception as e:
        logger.error("GCS upload failed for %s: %s", filename, e, exc_info=True)
        return f"error: {e}"


async def retrieve_receipt_image(
    gcs_uri: str,
    tool_context: ToolContext,
) -> bytes:
    """Download a receipt or invoice image from Google Cloud Storage.

    Call this tool when the user wants to view a previously stored
    receipt or invoice image. Accepts the GCS URI returned by
    store_receipt_image.

    Args:
        gcs_uri: The GCS URI (gs://bucket/path) of the image.
        tool_context: ADK tool context for session state access.

    Returns:
        bytes — the raw image data, or an empty bytes object on error.
    """
    try:
        # Parse gs://bucket/path
        if not gcs_uri.startswith("gs://"):
            raise ValueError(f"Invalid GCS URI: {gcs_uri}")

        without_prefix = gcs_uri[5:]  # Remove 'gs://'
        bucket_name, blob_path = without_prefix.split("/", 1)

        client = _get_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_path)

        data = blob.download_as_bytes()
        logger.info("Downloaded %d bytes from %s", len(data), gcs_uri)
        return data

    except Exception as e:
        logger.error("GCS download failed for %s: %s", gcs_uri, e, exc_info=True)
        return b""
