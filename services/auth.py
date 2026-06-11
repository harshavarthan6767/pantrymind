import os
from fastapi import Header

DEMO_USER_ID = os.getenv("DEMO_USER_ID", "demo_user_001")

async def get_current_user(
    x_user_id: str = Header(default=None),
    authorization: str = Header(default=None)
) -> str:
    """
    Hackathon auth: read user_id from Authorization: Bearer <id> or X-User-Id header.
    Falls back to DEMO_USER_ID for local dev.
    Post-hackathon: replace with Firebase/JWT token verification.
    """
    if authorization and authorization.startswith("Bearer "):
        uid = authorization[7:].strip()
        if uid:
            return uid
    if x_user_id:
        return x_user_id
    return DEMO_USER_ID
