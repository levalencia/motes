"""OAuth2 flows for connecting external services via consent screens.

Supports Google (Gmail, Calendar, Drive), GitHub, Slack, and any OAuth2 provider.
Admin configures client credentials once; users click Connect → consent screen → done.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

import httpx
import structlog
from sqlalchemy import DateTime, ForeignKey, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base

logger = structlog.get_logger()


class OAuthApp(Base):
    """Admin-configured OAuth application credentials (one per provider)."""

    __tablename__ = "oauth_apps"

    id: Mapped[str] = mapped_column(
        primary_key=True, default=lambda: str(uuid.uuid4())
    )
    provider: Mapped[str] = mapped_column(unique=True, index=True)
    # e.g. "google", "github", "slack"
    client_id: Mapped[str]
    client_secret_encrypted: Mapped[str]
    scopes: Mapped[str] = mapped_column(Text, default="")
    # extra config (JSON) — e.g. {"tenant": "common"} for Azure
    extra_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class OAuthToken(Base):
    """User's OAuth tokens for a connected service."""

    __tablename__ = "oauth_tokens"

    id: Mapped[str] = mapped_column(
        primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(index=True)
    # e.g. "google", "github", "slack"
    service: Mapped[str]
    # e.g. "gmail", "calendar", "github", "slack"
    access_token_encrypted: Mapped[str]
    refresh_token_encrypted: Mapped[str] = mapped_column(default="")
    token_type: Mapped[str] = mapped_column(default="Bearer")
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    scopes: Mapped[str] = mapped_column(Text, default="")
    account_email: Mapped[str] = mapped_column(default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ── Provider configurations ──────────────────────────────────────────

OAUTH_PROVIDERS: dict[str, dict[str, Any]] = {
    "google": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "services": {
            "gmail": {
                "scopes": [
                    "https://www.googleapis.com/auth/gmail.readonly",
                    "https://www.googleapis.com/auth/gmail.send",
                    "https://www.googleapis.com/auth/gmail.labels",
                ],
                "label": "Gmail",
            },
            "calendar": {
                "scopes": [
                    "https://www.googleapis.com/auth/calendar",
                    "https://www.googleapis.com/auth/calendar.events",
                ],
                "label": "Google Calendar",
            },
        },
        "base_scopes": [
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
        ],
    },
    "github": {
        "auth_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "services": {
            "github": {
                "scopes": ["repo", "read:org", "read:user"],
                "label": "GitHub",
            },
        },
        "base_scopes": [],
    },
    "slack": {
        "auth_url": "https://slack.com/oauth/v2/authorize",
        "token_url": "https://slack.com/api/oauth.v2.access",
        "userinfo_url": "https://slack.com/api/auth.test",
        "services": {
            "slack": {
                "scopes": [
                    "channels:read",
                    "channels:history",
                    "chat:write",
                    "users:read",
                ],
                "label": "Slack",
            },
        },
        "base_scopes": [],
    },
}


def build_auth_url(
    provider: str,
    service: str,
    client_id: str,
    redirect_uri: str,
    state: str,
) -> str:
    """Build the OAuth2 authorization URL for a provider+service."""
    config = OAUTH_PROVIDERS.get(provider)
    if not config:
        raise ValueError(f"Unknown OAuth provider: {provider}")

    svc_config = config["services"].get(service)
    if not svc_config:
        raise ValueError(f"Unknown service '{service}' for provider '{provider}'")

    scopes = config["base_scopes"] + svc_config["scopes"]

    params: dict[str, str] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "response_type": "code",
    }

    if provider == "google":
        params["scope"] = " ".join(scopes)
        params["access_type"] = "offline"
        params["prompt"] = "consent"
    elif provider == "github":
        params["scope"] = " ".join(scopes)
    elif provider == "slack":
        params["scope"] = ",".join(scopes)

    return f"{config['auth_url']}?{urlencode(params)}"


async def exchange_code(
    provider: str,
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> dict[str, Any]:
    """Exchange authorization code for tokens."""
    config = OAUTH_PROVIDERS.get(provider)
    if not config:
        raise ValueError(f"Unknown OAuth provider: {provider}")

    payload = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    headers: dict[str, str] = {"Accept": "application/json"}

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            config["token_url"], data=payload, headers=headers
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Token exchange failed: {resp.text[:300]}")
        return resp.json()


async def get_user_email(
    provider: str, access_token: str
) -> str:
    """Fetch the user's email from the provider."""
    config = OAUTH_PROVIDERS.get(provider)
    if not config or not config.get("userinfo_url"):
        return ""

    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(config["userinfo_url"], headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("email", data.get("login", ""))
    return ""


async def save_oauth_app(
    session: AsyncSession,
    provider: str,
    client_id: str,
    client_secret: str,
    scopes: str = "",
) -> OAuthApp:
    """Save or update OAuth app credentials (admin action)."""
    result = await session.execute(
        select(OAuthApp).where(OAuthApp.provider == provider)
    )
    app = result.scalar_one_or_none()
    if app:
        app.client_id = client_id
        app.client_secret_encrypted = client_secret
        if scopes:
            app.scopes = scopes
    else:
        app = OAuthApp(
            provider=provider,
            client_id=client_id,
            client_secret_encrypted=client_secret,
            scopes=scopes,
        )
        session.add(app)
    await session.commit()
    await session.refresh(app)
    return app


async def get_oauth_app(
    session: AsyncSession, provider: str
) -> OAuthApp | None:
    """Get OAuth app credentials for a provider."""
    result = await session.execute(
        select(OAuthApp).where(OAuthApp.provider == provider)
    )
    return result.scalar_one_or_none()


async def list_oauth_apps(
    session: AsyncSession,
) -> list[OAuthApp]:
    """List all configured OAuth apps."""
    result = await session.execute(
        select(OAuthApp).order_by(OAuthApp.provider)
    )
    return list(result.scalars().all())


async def save_token(
    session: AsyncSession,
    user_id: str,
    provider: str,
    service: str,
    access_token: str,
    refresh_token: str = "",
    scopes: str = "",
    account_email: str = "",
) -> OAuthToken:
    """Save or update a user's OAuth token for a service."""
    result = await session.execute(
        select(OAuthToken).where(
            OAuthToken.user_id == user_id,
            OAuthToken.service == service,
        )
    )
    token = result.scalar_one_or_none()
    if token:
        token.access_token_encrypted = access_token
        if refresh_token:
            token.refresh_token_encrypted = refresh_token
        token.scopes = scopes
        token.account_email = account_email
    else:
        token = OAuthToken(
            user_id=user_id,
            provider=provider,
            service=service,
            access_token_encrypted=access_token,
            refresh_token_encrypted=refresh_token,
            scopes=scopes,
            account_email=account_email,
        )
        session.add(token)
    await session.commit()
    await session.refresh(token)
    return token


async def list_connected_services(
    session: AsyncSession, user_id: str
) -> list[OAuthToken]:
    """List user's connected OAuth services."""
    result = await session.execute(
        select(OAuthToken)
        .where(OAuthToken.user_id == user_id)
        .order_by(OAuthToken.created_at)
    )
    return list(result.scalars().all())


async def disconnect_service(
    session: AsyncSession, user_id: str, service: str
) -> bool:
    """Remove a connected service."""
    result = await session.execute(
        select(OAuthToken).where(
            OAuthToken.user_id == user_id,
            OAuthToken.service == service,
        )
    )
    token = result.scalar_one_or_none()
    if not token:
        return False
    await session.delete(token)
    await session.commit()
    return True


def generate_state() -> str:
    """Generate a CSRF-safe state parameter."""
    return secrets.token_urlsafe(32)
