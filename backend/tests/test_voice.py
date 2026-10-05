"""Tests for voice I/O: STT and TTS."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.voice import (
    VoiceCapability,
    VoiceProviderType,
    test_stt_connection,
    test_tts_connection,
)


@pytest.mark.unit
class TestTTSConnection:
    """TTS connection testing."""

    @pytest.mark.asyncio
    async def test_successful_tts(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "audio/mpeg"}
        mock_response.content = b"\x00" * 200  # fake audio

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("app.voice.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            success, msg = await test_tts_connection("http://fake.local/v1", "key", "tts-1", "alloy")
            assert success is True

    @pytest.mark.asyncio
    async def test_tts_unreachable(self) -> None:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("fail"))

        with patch("app.voice.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            success, msg = await test_tts_connection("http://fake.local/v1", "key", "tts-1", "alloy")
            assert success is False
            assert "Cannot connect" in msg


@pytest.mark.unit
class TestSTTConnection:
    """STT connection testing."""

    @pytest.mark.asyncio
    async def test_stt_endpoint_reachable(self) -> None:
        """A 400 means the endpoint exists (just needs proper audio)."""
        mock_response = MagicMock()
        mock_response.status_code = 400

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("app.voice.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            success, msg = await test_stt_connection("http://fake.local/v1", "key", "whisper-1")
            assert success is True

    @pytest.mark.asyncio
    async def test_stt_unreachable(self) -> None:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("fail"))

        with patch("app.voice.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            success, msg = await test_stt_connection("http://fake.local/v1", "key", "whisper-1")
            assert success is False


@pytest.mark.unit
class TestVoiceModels:
    """Voice model and enum tests."""

    def test_provider_types(self) -> None:
        assert VoiceProviderType.OPENAI == "openai"
        assert VoiceProviderType.ELEVENLABS == "elevenlabs"
        assert VoiceProviderType.CUSTOM == "custom"

    def test_capabilities(self) -> None:
        assert VoiceCapability.STT == "stt"
        assert VoiceCapability.TTS == "tts"
        assert VoiceCapability.BOTH == "both"
