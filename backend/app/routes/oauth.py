"""OAuth routes: consent screen flows, admin app config, connected services."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_session
from app.models import User
from app.oauth import (
    OAUTH_PROVIDERS,
    build_auth_url,
    disconnect_service,
    exchange_code,
    generate_state,
    get_oauth_app,
    get_user_email,
    list_connected_services,
    list_oauth_apps,
    save_oauth_app,
    save_token,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/api/oauth", tags=["oauth"])

# In-memory state store (production would use Redis)
_pending_states: dict[str, dict] = {}


class OAuthAppCreate(BaseModel):
    provider: str = Field(min_length=1)
    client_id: str = Field(min_length=1)
    client_secret: str = Field(min_length=1)


class OAuthAppResponse(BaseModel):
    provider: str
    client_id: str
    is_configured: bool


class ConnectedServiceResponse(BaseModel):
    service: str
    provider: str
    account_email: str
    scopes: str


class AvailableServiceResponse(BaseModel):
    provider: str
    service: str
    label: str
    is_connected: bool
    is_configured: bool


@router.post("/apps", response_model=OAuthAppResponse, status_code=201)
async def configure_oauth_app(
    body: OAuthAppCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Admin: configure OAuth client credentials for a provider."""
    if body.provider not in OAUTH_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider. Available: {', '.join(OAUTH_PROVIDERS)}",
        )
    app = await save_oauth_app(session, body.provider, body.client_id, body.client_secret)
    return OAuthAppResponse(provider=app.provider, client_id=app.client_id, is_configured=True)


@router.get("/apps", response_model=list[OAuthAppResponse])
async def get_oauth_apps(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """List configured OAuth apps (client_id only, never secrets)."""
    apps = await list_oauth_apps(session)
    return [OAuthAppResponse(provider=a.provider, client_id=a.client_id, is_configured=True) for a in apps]


@router.get("/services", response_model=list[AvailableServiceResponse])
async def get_available_services(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """List all available OAuth services with connection status."""
    apps = await list_oauth_apps(session)
    configured_providers = {a.provider for a in apps}
    connected = await list_connected_services(session, user.id)
    connected_services = {t.service for t in connected}

    result = []
    for provider, config in OAUTH_PROVIDERS.items():
        for service, svc_config in config["services"].items():
            result.append(
                AvailableServiceResponse(
                    provider=provider,
                    service=service,
                    label=svc_config["label"],
                    is_connected=service in connected_services,
                    is_configured=provider in configured_providers,
                )
            )
    return result


@router.get("/connected", response_model=list[ConnectedServiceResponse])
async def get_connected_services(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """List user's connected services."""
    tokens = await list_connected_services(session, user.id)
    return [
        ConnectedServiceResponse(
            service=t.service,
            provider=t.provider,
            account_email=t.account_email,
            scopes=t.scopes,
        )
        for t in tokens
    ]


@router.get("/connect/{provider}/{service}")
async def start_oauth(
    provider: str,
    service: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Start OAuth flow: returns auth_url to redirect user to consent screen."""
    app = await get_oauth_app(session, provider)
    if app is None:
        raise HTTPException(
            status_code=400,
            detail=f"OAuth not configured for {provider}. Admin must add credentials in Settings first.",
        )

    state = generate_state()
    base = str(request.base_url).rstrip("/")
    redirect_uri = f"{base}/api/oauth/callback/{provider}"

    _pending_states[state] = {
        "user_id": user.id,
        "provider": provider,
        "service": service,
        "redirect_uri": redirect_uri,
    }

    auth_url = build_auth_url(provider, service, app.client_id, redirect_uri, state)
    return {"auth_url": auth_url}


@router.get("/callback/{provider}")
async def oauth_callback(
    provider: str,
    code: str,
    state: str,
    session: AsyncSession = Depends(get_session),
):
    """OAuth callback: exchanges code for tokens, saves, redirects to frontend."""
    pending = _pending_states.pop(state, None)
    if pending is None:
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    if pending["provider"] != provider:
        raise HTTPException(status_code=400, detail="Provider mismatch")

    app = await get_oauth_app(session, provider)
    if app is None:
        raise HTTPException(status_code=500, detail="OAuth app not found")

    tokens = await exchange_code(
        provider,
        code,
        app.client_id,
        app.client_secret_encrypted,
        pending["redirect_uri"],
    )

    access_token = tokens.get("access_token", "")
    refresh_token = tokens.get("refresh_token", "")
    scope = tokens.get("scope", "")

    email = await get_user_email(provider, access_token)

    await save_token(
        session,
        user_id=pending["user_id"],
        provider=provider,
        service=pending["service"],
        access_token=access_token,
        refresh_token=refresh_token,
        scopes=scope,
        account_email=email,
    )

    return RedirectResponse(url="http://localhost:5173/services?connected=" + pending["service"])


@router.delete("/connected/{service}", status_code=204)
async def disconnect(
    service: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Disconnect a service (revoke tokens)."""
    removed = await disconnect_service(session, user.id, service)
    if not removed:
        raise HTTPException(status_code=404, detail="Service not connected")
