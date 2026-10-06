"""Tests for image upload and vision analysis."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


class TestImageUploadEndpoint:
    @pytest.mark.asyncio
    async def test_upload_returns_url(self):
        """POST /api/agents/{id}/images with file returns a URL."""
        from app.routes.images import save_upload

        # Mock file
        mock_file = MagicMock()
        mock_file.filename = "receipt.jpg"
        mock_file.content_type = "image/jpeg"
        mock_file.read = AsyncMock(return_value=b"fake-image-data")

        result = await save_upload(mock_file, "test-agent-id")
        assert result["filename"] == "receipt.jpg"
        assert "url" in result
        assert result["content_type"] == "image/jpeg"


class TestVisionTool:
    def test_tool_name(self):
        from app.vision_tool import VisionTool

        tool = VisionTool(
            provider_url="https://example.com",
            api_key="test-key",
            model="claude-opus-4-6",
            api_format="anthropic",
        )
        assert tool.name == "analyze_image"
        assert "image" in tool.description.lower()

    def test_tool_parameters(self):
        from app.vision_tool import VisionTool

        tool = VisionTool(
            provider_url="https://example.com",
            api_key="test-key",
            model="claude-opus-4-6",
            api_format="anthropic",
        )
        params = tool.parameters
        assert params["type"] == "object"
        assert "image_url" in params["properties"]
        assert "question" in params["properties"]

    @pytest.mark.asyncio
    async def test_tool_returns_description(self):
        from app.vision_tool import VisionTool

        tool = VisionTool(
            provider_url="https://example.com",
            api_key="test-key",
            model="claude-opus-4-6",
            api_format="anthropic",
        )
        # Mock the HTTP call
        with patch("app.vision_tool.httpx") as mock_httpx:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "content": [{"type": "text", "text": "This is a receipt from Jumbo for €45.50"}]
            }
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_httpx.AsyncClient.return_value = mock_client

            result = await tool.execute(
                {
                    "image_url": "http://localhost:8001/uploads/test.jpg",
                    "question": "What is this receipt for?",
                }
            )
            parsed = json.loads(result)
            assert "receipt" in parsed["description"].lower() or "Jumbo" in parsed["description"]


class TestImageMessageFormat:
    def test_anthropic_image_content_block(self):
        """Anthropic expects image_url in a specific content block format."""
        from app.vision_tool import build_anthropic_vision_message

        msg = build_anthropic_vision_message(
            "http://localhost:8001/uploads/test.jpg",
            "What is this?",
        )
        assert msg["role"] == "user"
        assert len(msg["content"]) == 2
        assert msg["content"][0]["type"] == "image"
        assert msg["content"][1]["type"] == "text"
