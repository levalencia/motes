"""Tests for provider management."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.providers import test_provider_connection


@pytest.mark.unit
class TestProviderConnection:
    """Provider connection testing."""

    @pytest.mark.asyncio
    async def test_successful_connection(self) -> None:
        """Mock a successful OpenAI-compatible response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "ok"}}]}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("app.providers.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            success, message = await test_provider_connection("http://fake-api.local/v1", "fake-key", "fake-model")
            assert success is True
            assert "successful" in message.lower()

    @pytest.mark.asyncio
    async def test_unreachable_endpoint(self) -> None:
        """Test connection to unreachable endpoint."""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("fail"))

        with patch("app.providers.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            success, message = await test_provider_connection("http://unreachable.local/v1", "key", "model")
            assert success is False
            assert "Cannot connect" in message

    @pytest.mark.asyncio
    async def test_timeout(self) -> None:
        """Test connection timeout."""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        with patch("app.providers.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            success, message = await test_provider_connection("http://slow.local/v1", "key", "model")
            assert success is False
            assert "timed out" in message

    @pytest.mark.asyncio
    async def test_http_error(self) -> None:
        """Test HTTP error response."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("app.providers.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            success, message = await test_provider_connection("http://fake-api.local/v1", "bad-key", "model")
            assert success is False
            assert "401" in message
