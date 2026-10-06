"""Image upload endpoint — stores images and returns URLs for vision analysis."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.dependencies import get_current_user
from app.models import User

logger = structlog.get_logger()
router = APIRouter(prefix="/api", tags=["images"])

UPLOAD_DIR = Path(os.environ.get("MOTES_UPLOAD_DIR", "uploads"))
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/heic"}
MAX_SIZE = 10 * 1024 * 1024  # 10MB


async def save_upload(file: UploadFile, agent_id: str) -> dict:
    """Save an uploaded file and return metadata."""
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")

    ext = Path(file.filename or "image.jpg").suffix or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = UPLOAD_DIR / filename
    filepath.write_bytes(content)

    return {
        "filename": file.filename or filename,
        "stored_as": filename,
        "url": f"/uploads/{filename}",
        "content_type": file.content_type or "image/jpeg",
        "size": len(content),
    }


@router.post("/agents/{agent_id}/images")
async def upload_image(
    agent_id: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """Upload an image for vision analysis."""
    if file.content_type and file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported type: {file.content_type}")

    result = await save_upload(file, agent_id)
    logger.info("image_uploaded", filename=result["filename"], size=result["size"])
    return result
