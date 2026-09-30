"""FastAPI dependency injection: database sessions, auth, settings."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import decode_jwt
from app.config import Settings
from app.models import User

security = HTTPBearer(auto_error=False)


async def get_settings(request: Request) -> Settings:
    """Get application settings from app state."""
    return request.app.state.settings


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Get a database session from the app-scoped factory."""
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        yield session


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Authenticate the current user from JWT bearer token."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    settings: Settings = request.app.state.settings
    payload = decode_jwt(credentials.credentials, settings.secret_key)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user
