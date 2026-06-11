import asyncio
import logging
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable

logger = logging.getLogger(__name__)

async def call_gemini_with_retry(coro_factory, max_retries: int = 3):
    """
    Wrap any Gemini API call with exponential backoff.
    
    Usage:
        response = await call_gemini_with_retry(
            lambda: client.generate_content_async(prompt)
        )
    """
    for attempt in range(max_retries):
        try:
            return await coro_factory()
        except ResourceExhausted:
            if attempt == max_retries - 1:
                raise
            wait = (2 ** attempt) + (attempt * 0.5)
            logger.warning(f"Gemini rate limited. Retrying in {wait:.1f}s ({attempt+1}/{max_retries})")
            await asyncio.sleep(wait)
        except ServiceUnavailable:
            return {
                "status": "error",
                "reply": "AI service temporarily unavailable. Your data is safe — please retry."
            }

import time

def call_gemini_sync_with_retry(func, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            return func()
        except ResourceExhausted:
            if attempt == max_retries - 1:
                raise
            wait = (2 ** attempt) + (attempt * 0.5)
            logger.warning(f"Gemini rate limited. Retrying in {wait:.1f}s ({attempt+1}/{max_retries})")
            time.sleep(wait)
        except ServiceUnavailable:
            return {
                "status": "error",
                "reply": "AI service temporarily unavailable. Your data is safe — please retry."
            }
