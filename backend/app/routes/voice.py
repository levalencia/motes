"""Voice routes: STT/TTS provider management and audio endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_session
from app.models import User
from app.voice import (
    VoiceCapability,
    VoiceProviderType,
    add_voice_provider,
    get_voice_provider,
    list_voice_providers,
    synthesize_speech,
    transcribe_audio,
)

router = APIRouter(prefix="/api/voice", tags=["voice"])


class VoiceProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    provider_type: VoiceProviderType = VoiceProviderType.OPENAI
    capability: VoiceCapability = VoiceCapability.BOTH
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    stt_model: str = "whisper-1"
    tts_model: str = "tts-1"
    tts_voice: str = "alloy"


class VoiceProviderResponse(BaseModel):
    id: str
    name: str
    provider_type: str
    capability: str
    base_url: str
    stt_model: str
    tts_model: str
    tts_voice: str
    is_verified: bool


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4096)
    voice_provider_id: str | None = None  # None = use Edge TTS (free)
    voice: str | None = None
    response_format: str = "mp3"


class STTResponse(BaseModel):
    text: str


@router.post("/providers", response_model=VoiceProviderResponse, status_code=201)
async def create_voice_provider(
    body: VoiceProviderCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Add a voice provider. Tests connection first."""
    try:
        provider = await add_voice_provider(
            session, user.id, body.name, body.provider_type, body.capability,
            body.base_url, body.api_key, body.stt_model, body.tts_model, body.tts_voice,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return VoiceProviderResponse(
        id=provider.id, name=provider.name, provider_type=provider.provider_type,
        capability=provider.capability, base_url=provider.base_url,
        stt_model=provider.stt_model, tts_model=provider.tts_model,
        tts_voice=provider.tts_voice, is_verified=provider.is_verified,
    )


@router.get("/providers", response_model=list[VoiceProviderResponse])
async def get_voice_providers(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """List voice providers."""
    providers = await list_voice_providers(session, user.id)
    return [
        VoiceProviderResponse(
            id=p.id, name=p.name, provider_type=p.provider_type,
            capability=p.capability, base_url=p.base_url,
            stt_model=p.stt_model, tts_model=p.tts_model,
            tts_voice=p.tts_voice, is_verified=p.is_verified,
        )
        for p in providers
    ]


@router.post("/tts")
async def text_to_speech(
    body: TTSRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Convert text to speech audio. Uses Edge TTS (free) if no provider specified."""
    # Edge TTS — free, no provider needed
    if not body.voice_provider_id:
        from app.edge_tts_provider import edge_tts_synthesize

        voice = body.voice or "en-US-AriaNeural"
        try:
            audio = await edge_tts_synthesize(body.text, voice)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Edge TTS error: {exc}") from None
        return Response(content=audio, media_type="audio/mpeg")

    # Custom voice provider
    provider = await get_voice_provider(session, body.voice_provider_id, user.id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Voice provider not found")
    if provider.capability not in (VoiceCapability.TTS, VoiceCapability.BOTH):
        raise HTTPException(status_code=400, detail="Provider does not support TTS")

    voice = body.voice or provider.tts_voice
    try:
        audio = await synthesize_speech(
            provider.base_url, provider.api_key_encrypted,
            provider.tts_model, voice, body.text, body.response_format,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None

    media_type = {
        "mp3": "audio/mpeg",
        "opus": "audio/opus",
        "aac": "audio/aac",
        "flac": "audio/flac",
        "wav": "audio/wav",
        "pcm": "audio/pcm",
    }.get(body.response_format, "audio/mpeg")

    return Response(content=audio, media_type=media_type)


@router.post("/stt", response_model=STTResponse)
async def speech_to_text(
    file: UploadFile,
    voice_provider_id: str | None = None,
    language: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Transcribe audio to text. Uses local Whisper (free) if no provider specified."""
    audio_data = await file.read()
    if not audio_data:
        raise HTTPException(status_code=400, detail="Empty audio file")

    # Local Whisper — free, no provider needed
    if not voice_provider_id:
        from app.local_stt import transcribe_local

        try:
            text = await transcribe_local(audio_data, language)
        except Exception as exc:
            raise HTTPException(
                status_code=502, detail=f"Local STT error: {exc}"
            ) from None
        return STTResponse(text=text)

    # Server-side provider
    provider = await get_voice_provider(session, voice_provider_id, user.id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Voice provider not found")
    if provider.capability not in (VoiceCapability.STT, VoiceCapability.BOTH):
        raise HTTPException(status_code=400, detail="Provider does not support STT")

    try:
        text = await transcribe_audio(
            provider.base_url, provider.api_key_encrypted,
            provider.stt_model, audio_data,
            filename=file.filename or "audio.webm",
            language=language,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None

    return STTResponse(text=text)


# ── Realtime voice call settings ─────────────────────────────────


class RealtimeConfigResponse(BaseModel):
    realtime_url: str
    has_key: bool


class RealtimeConfigUpdate(BaseModel):
    realtime_url: str
    realtime_key: str


@router.get("/realtime-config", response_model=RealtimeConfigResponse)
async def get_realtime_config(
    request: Request,
    user: User = Depends(get_current_user),
):
    """Get realtime voice call config (key is never returned)."""
    settings = request.app.state.settings
    return RealtimeConfigResponse(
        realtime_url=settings.realtime_url,
        has_key=bool(settings.realtime_key),
    )


@router.post("/realtime-config", response_model=RealtimeConfigResponse)
async def set_realtime_config(
    body: RealtimeConfigUpdate,
    request: Request,
    user: User = Depends(get_current_user),
):
    """Save realtime voice call config. Stored in app state (runtime only)."""
    settings = request.app.state.settings
    settings.realtime_url = body.realtime_url
    settings.realtime_key = body.realtime_key
    return RealtimeConfigResponse(
        realtime_url=settings.realtime_url,
        has_key=bool(settings.realtime_key),
    )
