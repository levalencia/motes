"""Service keys — store and retrieve API keys for third-party integrations."""

from __future__ import annotations

import os

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.app_settings import get_setting, set_setting
from app.dependencies import get_current_user, get_session
from app.models import User

logger = structlog.get_logger()

router = APIRouter(prefix="/api/service-keys", tags=["service-keys"])

# Map service names to their env var keys
SERVICE_ENV_MAP = {
    "github": ["GITHUB_TOKEN"],
    "slack": ["SLACK_BOT_TOKEN"],
    "todoist": ["TODOIST_API_KEY"],
    "notion": ["NOTION_API_KEY"],
    "spotify": ["SPOTIFY_TOKEN"],
    "homeassistant": ["HA_URL", "HA_TOKEN"],
    "outlook": ["OUTLOOK_ACCESS_TOKEN"],
    "flights": ["AMADEUS_API_KEY", "AMADEUS_API_SECRET"],
    "telegram": ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"],
    "brave": ["BRAVE_SEARCH_API_KEY"],
}


class ServiceKeyRequest(BaseModel):
    service: str
    keys: dict[str, str]  # {"GITHUB_TOKEN": "ghp_xxx..."}


class ServiceKeyStatus(BaseModel):
    service: str
    configured: bool
    keys: list[str]  # Which env vars are set (names only, not values)


@router.get("", response_model=list[ServiceKeyStatus])
async def list_service_keys(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """List all services and whether they have keys configured."""
    result = []
    for service, env_vars in SERVICE_ENV_MAP.items():
        configured = True
        set_keys = []
        for var in env_vars:
            # Check DB first, then env
            db_val = await get_setting(session, f"service_key:{var}")
            env_val = os.environ.get(var, "")
            if db_val or env_val:
                set_keys.append(var)
            else:
                configured = False
        result.append(
            ServiceKeyStatus(
                service=service,
                configured=configured,
                keys=set_keys,
            )
        )
    return result


@router.post("")
async def save_service_key(
    body: ServiceKeyRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Save API keys for a service."""
    for key, value in body.keys.items():
        if value:  # Don't save empty values
            await set_setting(session, f"service_key:{key}", value)
            # Also set in current process env so tools pick it up immediately
            os.environ[key] = value
            logger.info("service_key_saved", service=body.service, key=key)
    return {"status": "ok", "service": body.service}


@router.delete("/{service}")
async def delete_service_key(
    service: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Remove API keys for a service."""
    env_vars = SERVICE_ENV_MAP.get(service, [])
    for var in env_vars:
        await set_setting(session, f"service_key:{var}", "")
        os.environ.pop(var, None)
    logger.info("service_key_deleted", service=service)
    return {"status": "ok"}
