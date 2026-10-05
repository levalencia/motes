"""Tests for MCP client — tool discovery, execution, and registry integration."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.mcp_client import (
    MCPClient,
    MCPServerConfig,
    MCPTool,
    load_mcp_servers,
)
from app.tools import ToolRegistry


@pytest.mark.unit
class TestMCPServerConfig:
    """Parsing MCP server config from dicts."""

    def test_parse_stdio_config(self) -> None:
        raw = {
            "name": "filesystem",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
            "env": {"HOME": "/root"},
        }
        cfg = MCPServerConfig.from_dict(raw)
        assert cfg.name == "filesystem"
        assert cfg.command == "npx"
        assert cfg.args == ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        assert cfg.env == {"HOME": "/root"}
        assert cfg.url is None
        assert cfg.transport == "stdio"

    def test_parse_http_config(self) -> None:
        raw = {
            "name": "remote-server",
            "url": "http://localhost:8080/mcp",
            "transport": "http",
        }
        cfg = MCPServerConfig.from_dict(raw)
        assert cfg.name == "remote-server"
        assert cfg.url == "http://localhost:8080/mcp"
        assert cfg.transport == "http"
        assert cfg.command is None

    def test_parse_minimal_config(self) -> None:
        raw = {"name": "test", "command": "echo"}
        cfg = MCPServerConfig.from_dict(raw)
        assert cfg.name == "test"
        assert cfg.command == "echo"
        assert cfg.args == []
        assert cfg.env == {}

    def test_parse_config_from_db_model(self) -> None:
        """Config can be built from MCPServer ORM fields."""
        raw = {
            "name": "gmail",
            "command": "npx @anthropic/mcp-gmail",
            "transport": "stdio",
            "env": {"GMAIL_TOKEN": "abc"},
        }
        cfg = MCPServerConfig.from_dict(raw)
        assert cfg.name == "gmail"
        assert cfg.transport == "stdio"


@pytest.mark.unit
class TestMCPToolDiscovery:
    """Discovering tools from a (mocked) MCP server."""

    @pytest.mark.asyncio
    async def test_discover_tools_from_server(self) -> None:
        """MCPClient.connect() returns discovered tool definitions."""
        mock_tools = [
            _make_mock_mcp_tool("read_file", "Read a file", {"path": {"type": "string"}}),
            _make_mock_mcp_tool(
                "write_file",
                "Write a file",
                {"path": {"type": "string"}, "content": {"type": "string"}},
            ),
        ]

        client = MCPClient()
        config = MCPServerConfig(name="fs-server", command="fake-cmd")

        with _mock_mcp_session(mock_tools):
            tools = await client.connect(config)

        assert len(tools) == 2
        assert tools[0].name == "mcp_fs_server__read_file"
        assert tools[1].name == "mcp_fs_server__write_file"
        assert "Read a file" in tools[0].description

    @pytest.mark.asyncio
    async def test_discover_tools_empty_server(self) -> None:
        """Server with no tools returns empty list."""
        client = MCPClient()
        config = MCPServerConfig(name="empty", command="noop")

        with _mock_mcp_session([]):
            tools = await client.connect(config)

        assert tools == []


@pytest.mark.unit
class TestMCPToolExecution:
    """Calling a tool on an MCP server."""

    @pytest.mark.asyncio
    async def test_mcp_tool_execution(self) -> None:
        """MCPTool.execute() calls the remote MCP server tool."""
        mock_result = MagicMock()
        mock_result.content = [MagicMock(text='{"status": "ok", "data": [1,2,3]}')]
        mock_result.isError = False

        mock_session = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=mock_result)

        tool = MCPTool(
            tool_name="read_file",
            server_name="fs-server",
            tool_description="Read a file",
            tool_parameters={"type": "object", "properties": {"path": {"type": "string"}}},
            session=mock_session,
        )

        result = await tool.execute({"path": "/tmp/test.txt"})
        parsed = json.loads(result)
        assert parsed["status"] == "ok"
        mock_session.call_tool.assert_called_once_with("read_file", arguments={"path": "/tmp/test.txt"})

    @pytest.mark.asyncio
    async def test_mcp_tool_execution_error(self) -> None:
        """MCPTool.execute() returns error JSON when the MCP call fails."""
        mock_result = MagicMock()
        mock_result.content = [MagicMock(text="Something went wrong")]
        mock_result.isError = True

        mock_session = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=mock_result)

        tool = MCPTool(
            tool_name="bad_tool",
            server_name="test",
            tool_description="A tool that fails",
            tool_parameters={"type": "object", "properties": {}},
            session=mock_session,
        )

        result = await tool.execute({})
        parsed = json.loads(result)
        assert "error" in parsed

    @pytest.mark.asyncio
    async def test_mcp_tool_execution_exception(self) -> None:
        """MCPTool.execute() handles transport exceptions gracefully."""
        mock_session = AsyncMock()
        mock_session.call_tool = AsyncMock(side_effect=Exception("connection lost"))

        tool = MCPTool(
            tool_name="some_tool",
            server_name="test",
            tool_description="desc",
            tool_parameters={"type": "object", "properties": {}},
            session=mock_session,
        )

        result = await tool.execute({})
        parsed = json.loads(result)
        assert "error" in parsed
        assert "connection lost" in parsed["error"]


@pytest.mark.unit
class TestMCPToolRegistration:
    """MCP tools register correctly in ToolRegistry."""

    def test_mcp_tool_registers_in_registry(self) -> None:
        """MCPTool instances can be added to ToolRegistry."""
        registry = ToolRegistry()
        mock_session = AsyncMock()

        tool = MCPTool(
            tool_name="search",
            server_name="github",
            tool_description="Search GitHub repos",
            tool_parameters={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            session=mock_session,
        )

        registry.register(tool)
        assert registry.get("mcp_github__search") is not None

        # Verify OpenAI tool format
        oai_tools = registry.to_openai_tools()
        assert len(oai_tools) == 1
        fn = oai_tools[0]["function"]
        assert fn["name"] == "mcp_github__search"
        assert fn["description"] == "Search GitHub repos"
        assert "query" in fn["parameters"]["properties"]

    def test_multiple_mcp_tools_no_collision(self) -> None:
        """Tools from different servers don't collide in the registry."""
        registry = ToolRegistry()
        mock_session = AsyncMock()

        tool1 = MCPTool(
            tool_name="search",
            server_name="github",
            tool_description="GitHub search",
            tool_parameters={"type": "object", "properties": {}},
            session=mock_session,
        )
        tool2 = MCPTool(
            tool_name="search",
            server_name="slack",
            tool_description="Slack search",
            tool_parameters={"type": "object", "properties": {}},
            session=mock_session,
        )

        registry.register(tool1)
        registry.register(tool2)

        assert registry.get("mcp_github__search") is not None
        assert registry.get("mcp_slack__search") is not None
        assert len(registry.list_tools()) == 2


@pytest.mark.unit
class TestMCPConnectionFailure:
    """Graceful handling of MCP server failures."""

    @pytest.mark.asyncio
    async def test_mcp_server_connection_failure(self) -> None:
        """connect() returns empty list and logs on connection failure."""
        client = MCPClient()
        config = MCPServerConfig(name="broken", command="nonexistent-binary-xyz")

        with patch.object(client, "_connect_stdio", side_effect=Exception("spawn failed")):
            tools = await client.connect(config)

        assert tools == []

    @pytest.mark.asyncio
    async def test_mcp_server_connection_failure_http(self) -> None:
        """HTTP connection failure returns empty list."""
        client = MCPClient()
        config = MCPServerConfig(name="remote", url="http://localhost:99999/mcp", transport="http")

        with patch.object(client, "_connect_http", side_effect=Exception("refused")):
            tools = await client.connect(config)

        assert tools == []


@pytest.mark.unit
class TestMCPStdioTransport:
    """Stdio transport specifics."""

    @pytest.mark.asyncio
    async def test_mcp_stdio_transport(self) -> None:
        """Stdio transport launches a subprocess and discovers tools."""
        mock_tools = [
            _make_mock_mcp_tool("list_files", "List files in dir", {"dir": {"type": "string"}}),
        ]

        client = MCPClient()
        config = MCPServerConfig(
            name="files",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem"],
            env={"NODE_PATH": "/usr/lib/node"},
        )

        with _mock_mcp_session(mock_tools):
            tools = await client.connect(config)

        assert len(tools) == 1
        assert tools[0].name == "mcp_files__list_files"

    @pytest.mark.asyncio
    async def test_mcp_stdio_command_with_args(self) -> None:
        """Command args are passed through to stdio transport."""
        mock_tools = [_make_mock_mcp_tool("ping", "Ping tool", {})]

        client = MCPClient()
        config = MCPServerConfig(
            name="test",
            command="python",
            args=["-m", "my_mcp_server", "--port", "0"],
        )

        with _mock_mcp_session(mock_tools):
            tools = await client.connect(config)

        assert len(tools) == 1


@pytest.mark.unit
class TestLoadMCPServers:
    """load_mcp_servers integration."""

    @pytest.mark.asyncio
    async def test_load_mcp_servers_from_config_list(self) -> None:
        """load_mcp_servers processes multiple configs."""
        configs = [
            {"name": "server-a", "command": "cmd-a"},
            {"name": "server-b", "command": "cmd-b"},
        ]

        call_count = 0

        async def fake_connect(config: MCPServerConfig) -> list[MCPTool]:
            nonlocal call_count
            call_count += 1
            if config.name == "server-a":
                return [MCPTool("tool_a", "server_a", "Tool A", {"type": "object", "properties": {}}, AsyncMock())]
            return [MCPTool("tool_b", "server_b", "Tool B", {"type": "object", "properties": {}}, AsyncMock())]

        with patch("app.mcp_client.MCPClient.connect", side_effect=fake_connect):
            tools = await load_mcp_servers(configs)

        assert len(tools) == 2
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_load_mcp_servers_partial_failure(self) -> None:
        """If one server fails, others still load."""
        configs = [
            {"name": "good", "command": "good-cmd"},
            {"name": "bad", "command": "bad-cmd"},
        ]

        async def fake_connect(config: MCPServerConfig) -> list[MCPTool]:
            if config.name == "bad":
                raise Exception("server down")
            return [MCPTool("tool_g", "good", "Good tool", {"type": "object", "properties": {}}, AsyncMock())]

        with patch("app.mcp_client.MCPClient.connect", side_effect=fake_connect):
            tools = await load_mcp_servers(configs)

        assert len(tools) == 1
        assert tools[0].name == "mcp_good__tool_g"


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_mock_mcp_tool(name: str, description: str, properties: dict[str, Any]) -> MagicMock:
    """Create a mock MCP tool definition (as returned by session.list_tools())."""
    tool = MagicMock()
    tool.name = name
    tool.description = description
    tool.inputSchema = {
        "type": "object",
        "properties": properties,
    }
    return tool


def _mock_mcp_session(tools: list[MagicMock]):
    """Context manager that patches MCPClient._connect_stdio to return a mock session."""
    mock_session = AsyncMock()
    mock_session.list_tools = AsyncMock(return_value=tools)

    async def fake_connect_stdio(self_client, config):
        return mock_session

    async def fake_connect_http(self_client, config):
        return mock_session

    return patch.multiple(
        "app.mcp_client.MCPClient",
        _connect_stdio=fake_connect_stdio,
        _connect_http=fake_connect_http,
    )
