"""Provider routes: add, list, test, delete OpenAI-compatible endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_session
from app.models import User
from app.providers import add_provider, delete_provider, list_providers, test_provider_connection

router = APIRouter(prefix="/api/providers", tags=["providers"])


class ProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    base_url: str = Field(min_length=1)
    api_key: str = Field(min_length=1)
    model: str = Field(min_length=1)
    api_format: str = "openai"  # openai | anthropic


class ProviderTestRequest(BaseModel):
    base_url: str
    api_key: str
    model: str


class ProviderResponse(BaseModel):
    id: str
    name: str
    base_url: str
    model: str
    is_verified: bool


class ProviderTestResponse(BaseModel):
    success: bool
    message: str


@router.post("/test", response_model=ProviderTestResponse)
async def test_provider(
    body: ProviderTestRequest,
    user: User = Depends(get_current_user),
):
    """Test an OpenAI-compatible endpoint without saving it."""
    success, message = await test_provider_connection(body.base_url, body.api_key, body.model)
    return ProviderTestResponse(success=success, message=message)


@router.post("", response_model=ProviderResponse, status_code=201)
async def create_provider(
    body: ProviderCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Add a new provider. Tests connection first, rejects if invalid."""
    try:
        provider = await add_provider(
            session, user.id, body.name, body.base_url, body.api_key, body.model,
            body.api_format,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return ProviderResponse(
        id=provider.id,
        name=provider.name,
        base_url=provider.base_url,
        model=provider.model,
        is_verified=provider.is_verified,
    )


@router.get("", response_model=list[ProviderResponse])
async def get_providers(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """List all providers for the current user."""
    providers = await list_providers(session, user.id)
    return [
        ProviderResponse(
            id=p.id, name=p.name, base_url=p.base_url, model=p.model, is_verified=p.is_verified
        )
        for p in providers
    ]


@router.delete("/{provider_id}", status_code=204)
async def remove_provider(
    provider_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Delete a provider."""
    deleted = await delete_provider(session, provider_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Provider not found")
