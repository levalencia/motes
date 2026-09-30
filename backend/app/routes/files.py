"""File routes: download files from the host machine."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.dependencies import get_current_user
from app.models import User

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/download")
async def download_file(
    path: str,
    user: User = Depends(get_current_user),
):
    """Download a file from the host machine."""
    file_path = Path(path).expanduser().resolve()
    home = Path.home().resolve()

    # Security: only allow files under home directory
    if not str(file_path).startswith(str(home)):
        raise HTTPException(status_code=403, detail="Access denied")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream",
    )
