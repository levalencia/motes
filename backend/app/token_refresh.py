"""OAuth token refresh — automatically refresh expired Google/GitHub tokens."""

from __future__ import annotations

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.oauth import OAuthToken, get_oauth_app

logger = structlog.get_logger()


async def refresh_google_token(
    session: AsyncSession, token: OAuthToken
) -> str:
    """Refresh a Google OAuth token. Returns new access token."""
    app = await get_oauth_app(session, "google")
    if not app or not token.refresh_token_encrypted:
        raise RuntimeError("Cannot refresh: missing app credentials or refresh token")

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": app.client_id,
                "client_secret": app.client_secret_encrypted,
                "refresh_token": token.refresh_token_encrypted,
                "grant_type": "refresh_token",
            },
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Token refresh failed: {resp.text[:200]}")

        data = resp.json()
        new_access_token = data["access_token"]

        # Update in DB
        token.access_token_encrypted = new_access_token
        await session.commit()

        return new_access_token


async def get_valid_token(
    session: AsyncSession, user_id: str, service: str
) -> str | None:
    """Get a valid access token for a service, refreshing if needed."""
    result = await session.execute(
        select(OAuthToken).where(
            OAuthToken.user_id == user_id,
            OAuthToken.service == service,
        )
    )
    token = result.scalar_one_or_none()
    if not token:
        return None

    # Test if token still works
    if token.provider == "google":
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {token.access_token_encrypted}"},
            )
            if resp.status_code == 401:
                # Token expired — refresh it
                try:
                    return await refresh_google_token(session, token)
                except RuntimeError:
                    return None
            if resp.status_code == 200:
                return token.access_token_encrypted

    return token.access_token_encrypted
