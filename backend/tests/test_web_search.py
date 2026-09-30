"""Tests for web search tool."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.web_search_tool import WebSearchTool

pytestmark = pytest.mark.unit


class TestWebSearchTool:
    def test_tool_metadata(self):
        tool = WebSearchTool()
        assert tool.name == "web_search"
        assert "search" in tool.description.lower()
        assert "query" in tool.parameters["properties"]

    @pytest.mark.asyncio
    async def test_empty_query(self):
        tool = WebSearchTool()
        result = json.loads(await tool.execute({"query": ""}))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_ddg_search_mock(self):
        tool = WebSearchTool()  # No brave key = uses DDG
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<a class="result__a" href="http://example.com">Test Result</a>'

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = json.loads(await tool.execute({"query": "test"}))
            assert "results" in result

    @pytest.mark.asyncio
    async def test_brave_search_mock(self):
        tool = WebSearchTool(brave_api_key="test-key")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "web": {"results": [{"title": "T", "url": "http://x", "description": "D"}]}
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = json.loads(await tool.execute({"query": "test"}))
            assert len(result["results"]) == 1
            assert result["results"][0]["title"] == "T"
