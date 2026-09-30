"""Provider management: add, test, list OpenAI-compatible endpoints."""

from __future__ import annotations

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Provider

logger = structlog.get_logger()


async def test_provider_connection(
    base_url: str, api_key: str, model: str, timeout: float = 10.0
) -> tuple[bool, str]:
    """Test an OpenAI-compatible endpoint with a tiny completion.

    Returns
    """
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Say 'ok'"}],
        "max_tokens": 5,
        "temperature": 0,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                data = response.json()
                # Verify we got a valid completion response
                if "choices" in data and len(data["choices"]) > 0:
                    return True, "Connection successful"
                return False, f"Unexpected response format: {data}"
            return False, f"HTTP {response.status_code}: {response.text[:200]}"
    except httpx.ConnectError:
        return False, f"Cannot connect to {base_url}"
    except httpx.TimeoutException:
        return False, f"Connection to {base_url} timed out after {timeout}s"
    except Exception as exc:
        return False, f"Connection error: {exc}"


async def test_anthropic_connection(
    base_url: str, api_key: str, model: str, timeout: float = 10.0
) -> tuple[bool, str]:
    """Test an Anthropic Messages API endpoint."""
    url = base_url.rstrip("/") + "/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Say ok"}],
        "max_tokens": 5,
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if "content" in data:
                    return True, "Connection successful"
                return False, f"Unexpected response: {data}"
            return False, f"HTTP {response.status_code}: {response.text[:200]}"
    except httpx.ConnectError:
        return False, f"Cannot connect to {base_url}"
    except httpx.TimeoutException:
        return False, "Connection timed out"
    except Exception as exc:
        return False, f"Connection error: {exc}"


async def add_provider(
    session: AsyncSession,
    user_id: str,
    name: str,
    base_url: str,
    api_key: str,
    model: str,
    api_format: str = "openai",
) -> Provider:
    """Add a verified provider. Tests connection first, rejects if invalid."""
    if api_format == "anthropic":
        success, message = await test_anthropic_connection(base_url, api_key, model)
    else:
        success, message = await test_provider_connection(base_url, api_key, model)
    if not success:
        raise ValueError(f"Provider validation failed: {message}")

    provider = Provider(
        user_id=user_id,
        name=name,
        base_url=base_url.rstrip("/"),
        api_key_encrypted=api_key,  # TODO: encrypt at rest
        model=model,
        api_format=api_format,
        is_verified=True,
    )
    session.add(provider)
    await session.commit()
    await session.refresh(provider)
    return provider


async def list_providers(session: AsyncSession, user_id: str) -> list[Provider]:
    """List all providers for a user."""
    result = await session.execute(
        select(Provider).where(Provider.user_id == user_id).order_by(Provider.created_at)
    )
    return list(result.scalars().all())


async def get_provider(session: AsyncSession, provider_id: str, user_id: str) -> Provider | None:
    """Get a specific provider by ID, scoped to user."""
    result = await session.execute(
        select(Provider).where(Provider.id == provider_id, Provider.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def delete_provider(session: AsyncSession, provider_id: str, user_id: str) -> bool:
    """Delete a provider. Returns True if found and deleted."""
    provider = await get_provider(session, provider_id, user_id)
    if provider is None:
        return False
    await session.delete(provider)
    await session.commit()
    return True
