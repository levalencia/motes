"""Tests for MCP Proxy Service — persistent HTTP MCP connections."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit


class TestMCPProxyServiceInit:
    def test_init(self):
        from app.mcp_proxy import MCPProxyService

        service = MCPProxyService()
        assert service._connections == {}

    def test_is_connected_false(self):
        from app.mcp_proxy import MCPProxyService

        service = MCPProxyService()
        assert service.is_connected("test") is False

    def test_get_tool_schemas_empty(self):
        from app.mcp_proxy import MCPProxyService

        service = MCPProxyService()
        assert service.get_tool_schemas("test") == {}

    def test_all_tool_schemas_empty(self):
        from app.mcp_proxy import MCPProxyService

        service = MCPProxyService()
        assert service.all_tool_schemas() == {}


class TestMCPProxyServiceCallTool:
    @pytest.mark.asyncio
    async def test_call_tool_not_connected(self):
        from app.mcp_proxy import MCPProxyService

        service = MCPProxyService()
        result = await service.call_tool("unknown", "tool", {})
        assert "error" in result
        assert "not connected" in result["error"].lower()


class TestMCPProxyServiceConnection:
    def test_connection_dataclass(self):
        from app.mcp_proxy import MCPConnection

        conn = MCPConnection(server_name="test", url="https://example.com/mcp")
        assert conn.server_name == "test"
        assert conn.url == "https://example.com/mcp"
        assert conn.tools == {}
        assert conn.session is None

    def test_is_connected_after_manual_add(self):
        from app.mcp_proxy import MCPConnection, MCPProxyService

        service = MCPProxyService()
        conn = MCPConnection(server_name="test", url="https://example.com")
        conn.session = MagicMock()  # simulate active session
        conn.tools = {"read": {"name": "read", "description": "Read"}}
        service._connections["test"] = conn
        assert service.is_connected("test") is True
        assert service.get_tool_schemas("test") == {"read": {"name": "read", "description": "Read"}}

    def test_all_tool_schemas_namespaced(self):
        from app.mcp_proxy import MCPConnection, MCPProxyService

        service = MCPProxyService()
        conn = MCPConnection(server_name="ship-page", url="https://ship.page/mcp")
        conn.tools = {
            "deploy_html": {"name": "deploy_html", "description": "Deploy"},
            "list_drops": {"name": "list_drops", "description": "List"},
        }
        service._connections["ship-page"] = conn
        schemas = service.all_tool_schemas()
        assert "mcp_ship-page__deploy_html" in schemas
        assert "mcp_ship-page__list_drops" in schemas

    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self):
        from app.mcp_proxy import MCPConnection, MCPProxyService

        service = MCPProxyService()
        conn = MCPConnection(server_name="test", url="https://example.com")
        conn._task = MagicMock()
        conn._task.cancel = MagicMock()
        service._connections["test"] = conn

        await service.disconnect("test")
        assert service.is_connected("test") is False
        conn._task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_all(self):
        from app.mcp_proxy import MCPConnection, MCPProxyService

        service = MCPProxyService()
        for name in ["a", "b", "c"]:
            conn = MCPConnection(server_name=name, url=f"https://{name}.com")
            conn._task = MagicMock()
            conn._task.cancel = MagicMock()
            service._connections[name] = conn

        await service.disconnect_all()
        assert len(service._connections) == 0


class TestMCPProxyTool:
    def test_tool_name(self):
        from app.mcp_proxy import MCPProxyService, MCPProxyTool

        proxy = MCPProxyService()
        tool = MCPProxyTool(
            tool_name="deploy_html",
            server_name="ship-page",
            tool_description="Deploy an HTML page",
            tool_parameters={"type": "object"},
            proxy=proxy,
        )
        assert tool.name == "mcp_ship_page__deploy_html"
        assert tool.description == "Deploy an HTML page"
        assert tool.parameters == {"type": "object"}

    @pytest.mark.asyncio
    async def test_tool_execute_not_connected(self):
        from app.mcp_proxy import MCPProxyService, MCPProxyTool

        proxy = MCPProxyService()
        tool = MCPProxyTool(
            tool_name="deploy_html",
            server_name="ship-page",
            tool_description="Deploy",
            tool_parameters={},
            proxy=proxy,
        )
        result = await tool.execute({"html": "<h1>Hi</h1>"})
        parsed = json.loads(result)
        assert "error" in parsed
        assert "not connected" in parsed["error"].lower()

    @pytest.mark.asyncio
    async def test_tool_execute_with_mock_proxy(self):
        from app.mcp_proxy import MCPProxyService, MCPProxyTool

        proxy = MCPProxyService()
        proxy.call_tool = AsyncMock(return_value={"result": "https://example.ship.page"})
        tool = MCPProxyTool(
            tool_name="deploy_html",
            server_name="ship-page",
            tool_description="Deploy",
            tool_parameters={},
            proxy=proxy,
        )
        result = await tool.execute({"html": "<h1>Hi</h1>"})
        parsed = json.loads(result)
        assert parsed["result"] == "https://example.ship.page"
        proxy.call_tool.assert_called_once_with("ship-page", "deploy_html", {"html": "<h1>Hi</h1>"})
