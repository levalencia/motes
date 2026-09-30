"""Auth routes: setup, login."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import authenticate, create_jwt, is_setup_complete, setup_first_user
from app.dependencies import get_session, get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


class SetupRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    token: str
    user_id: str
    username: str


class SetupStatusResponse(BaseModel):
    is_setup_complete: bool


@router.get("/setup-status", response_model=SetupStatusResponse)
async def get_setup_status(session: AsyncSession = Depends(get_session)):
    """Check if first-user setup has been completed."""
    done = await is_setup_complete(session)
    return SetupStatusResponse(is_setup_complete=done)


@router.post("/setup", response_model=TokenResponse)
async def setup(
    body: SetupRequest,
    session: AsyncSession = Depends(get_session),
    settings=Depends(get_settings),
):
    """First-run setup: create the admin user."""
    try:
        user = await setup_first_user(session, body.username, body.password)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    token = create_jwt(user.id, settings.secret_key)
    return TokenResponse(token=token, user_id=user.id, username=user.username)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
    settings=Depends(get_settings),
):
    """Login with username + password."""
    user = await authenticate(session, body.username, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_jwt(user.id, settings.secret_key)
    return TokenResponse(token=token, user_id=user.id, username=user.username)
