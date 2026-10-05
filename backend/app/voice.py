"""Voice I/O: provider-agnostic STT (speech-to-text) and TTS (text-to-speech).

Supports any OpenAI-compatible voice API, plus extensible for ElevenLabs,
Azure Speech, Edge TTS, local Whisper, etc.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

import httpx
import structlog
from sqlalchemy import DateTime, ForeignKey, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base

logger = structlog.get_logger()


class VoiceProviderType(StrEnum):
    """Supported voice provider types."""

    OPENAI = "openai"  # OpenAI Whisper (STT) + TTS
    ELEVENLABS = "elevenlabs"  # ElevenLabs TTS
    AZURE = "azure"  # Azure Speech Services
    EDGE = "edge"  # Edge TTS (free, no API key)
    CUSTOM = "custom"  # Any OpenAI-compatible endpoint


class VoiceCapability(StrEnum):
    """What a voice provider can do."""

    STT = "stt"  # Speech-to-text
    TTS = "tts"  # Text-to-speech
    BOTH = "both"


class VoiceProvider(Base):
    """A configured voice provider (STT/TTS endpoint)."""

    __tablename__ = "voice_providers"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str]
    provider_type: Mapped[str] = mapped_column(default=VoiceProviderType.OPENAI)
    capability: Mapped[str] = mapped_column(default=VoiceCapability.BOTH)
    base_url: Mapped[str] = mapped_column(default="https://api.openai.com/v1")
    api_key_encrypted: Mapped[str] = mapped_column(default="")
    stt_model: Mapped[str] = mapped_column(default="whisper-1")
    tts_model: Mapped[str] = mapped_column(default="tts-1")
    tts_voice: Mapped[str] = mapped_column(default="alloy")
    is_verified: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


async def test_tts_connection(
    base_url: str,
    api_key: str,
    model: str,
    voice: str,
    timeout: float = 15.0,
) -> tuple[bool, str]:
    """Test a TTS endpoint with a tiny request."""
    url = base_url.rstrip("/") + "/audio/speech"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "input": "Test.",
        "voice": voice,
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                ct = resp.headers.get("content-type", "")
                if "audio" in ct or "octet" in ct or len(resp.content) > 100:
                    return True, "TTS connection successful"
                return False, f"Unexpected response: {ct}"
            return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
    except httpx.ConnectError:
        return False, f"Cannot connect to {base_url}"
    except httpx.TimeoutException:
        return False, "TTS endpoint timed out"
    except Exception as exc:
        return False, f"TTS error: {exc}"


async def test_stt_connection(
    base_url: str,
    api_key: str,
    model: str,
    timeout: float = 15.0,
) -> tuple[bool, str]:
    """Test an STT endpoint.

    We can't easily test without audio, so we verify the endpoint exists.
    """
    url = base_url.rstrip("/") + "/audio/transcriptions"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # Send a minimal request — it will fail with a validation error,
            # but a 400 proves the endpoint exists (vs 404/connection error)
            resp = await client.post(url, headers=headers, data={"model": model})
            if resp.status_code in (200, 400, 422):
                return True, "STT endpoint reachable"
            return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
    except httpx.ConnectError:
        return False, f"Cannot connect to {base_url}"
    except httpx.TimeoutException:
        return False, "STT endpoint timed out"
    except Exception as exc:
        return False, f"STT error: {exc}"


async def synthesize_speech(
    base_url: str,
    api_key: str,
    model: str,
    voice: str,
    text: str,
    response_format: str = "mp3",
) -> bytes:
    """Convert text to speech audio bytes via OpenAI-compatible API."""
    url = base_url.rstrip("/") + "/audio/speech"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "input": text,
        "voice": voice,
        "response_format": response_format,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"TTS failed: HTTP {resp.status_code}")
        return resp.content


async def transcribe_audio(
    base_url: str,
    api_key: str,
    model: str,
    audio_data: bytes,
    filename: str = "audio.webm",
    language: str | None = None,
) -> str:
    """Transcribe audio bytes to text via OpenAI-compatible API."""
    url = base_url.rstrip("/") + "/audio/transcriptions"
    headers = {"Authorization": f"Bearer {api_key}"}
    files = {"file": (filename, audio_data)}
    data: dict[str, str] = {"model": model}
    if language:
        data["language"] = language
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers, files=files, data=data)
        if resp.status_code != 200:
            raise RuntimeError(f"STT failed: HTTP {resp.status_code}")
        result = resp.json()
        return result.get("text", "")


async def add_voice_provider(
    session: AsyncSession,
    user_id: str,
    name: str,
    provider_type: str,
    capability: str,
    base_url: str,
    api_key: str,
    stt_model: str,
    tts_model: str,
    tts_voice: str,
) -> VoiceProvider:
    """Add a voice provider after testing it."""
    # Test based on capability
    if capability in (VoiceCapability.TTS, VoiceCapability.BOTH):
        success, msg = await test_tts_connection(base_url, api_key, tts_model, tts_voice)
        if not success:
            raise ValueError(f"TTS validation failed: {msg}")

    if capability in (VoiceCapability.STT, VoiceCapability.BOTH):
        success, msg = await test_stt_connection(base_url, api_key, stt_model)
        if not success:
            raise ValueError(f"STT validation failed: {msg}")

    provider = VoiceProvider(
        user_id=user_id,
        name=name,
        provider_type=provider_type,
        capability=capability,
        base_url=base_url.rstrip("/"),
        api_key_encrypted=api_key,
        stt_model=stt_model,
        tts_model=tts_model,
        tts_voice=tts_voice,
        is_verified=True,
    )
    session.add(provider)
    await session.commit()
    await session.refresh(provider)
    return provider


async def list_voice_providers(session: AsyncSession, user_id: str) -> list[VoiceProvider]:
    """List voice providers for a user."""
    result = await session.execute(
        select(VoiceProvider).where(VoiceProvider.user_id == user_id).order_by(VoiceProvider.created_at)
    )
    return list(result.scalars().all())


async def get_voice_provider(session: AsyncSession, provider_id: str, user_id: str) -> VoiceProvider | None:
    """Get a specific voice provider."""
    result = await session.execute(
        select(VoiceProvider).where(
            VoiceProvider.id == provider_id,
            VoiceProvider.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()
