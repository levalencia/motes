"""MCP client — connect to external MCP servers, discover tools, call them.

This module provides:
- MCPServerConfig: parsed config for an MCP server
- MCPClient: connects to stdio/http MCP servers, discovers tools
- MCPTool: wraps a remote MCP tool as a local Tool (compatible with ToolRegistry)
- load_mcp_servers(): batch-load tools from multiple MCP server configs
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class MCPServerConfig:
    """Configuration for connecting to an MCP server."""

    name: str
    command: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    url: str | None = None
    transport: str = "stdio"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MCPServerConfig:
        """Parse config from a plain dict (DB row, JSON, etc.)."""
        transport = data.get("transport", "stdio")
        if "url" in data and data["url"] and transport != "stdio":
            transport = data.get("transport", "http")

        return cls(
            name=data["name"],
            command=data.get("command"),
            args=data.get("args", []),
            env=data.get("env", {}),
            url=data.get("url"),
            transport=transport,
        )


def _sanitize_name(name: str) -> str:
    """Convert a server name to a safe identifier component."""
    return re.sub(r"[^a-zA-Z0-9]", "_", name).strip("_").lower()


class MCPTool:
    """Wraps a remote MCP server tool as a local Tool for ToolRegistry."""

    def __init__(
        self,
        tool_name: str,
        server_name: str,
        tool_description: str,
        tool_parameters: dict[str, Any],
        session: Any,  # MCP ClientSession or mock
    ) -> None:
        self._tool_name = tool_name
        self._server_name = server_name
        self._description = tool_description
        self._parameters = tool_parameters
        self._session = session

    @property
    def name(self) -> str:
        """Namespaced tool name: mcp_{server}__{tool}."""
        safe_server = _sanitize_name(self._server_name)
        return f"mcp_{safe_server}__{self._tool_name}"

    @property
    def description(self) -> str:
        return self._description

    @property
    def parameters(self) -> dict[str, Any]:
        return self._parameters

    async def execute(self, arguments: dict[str, Any]) -> str:
        """Call the tool on the remote MCP server."""
        try:
            result = await self._session.call_tool(self._tool_name, arguments=arguments)
            # Extract text from result content
            texts = []
            for content_item in result.content:
                if hasattr(content_item, "text"):
                    texts.append(content_item.text)

            combined = "\n".join(texts) if texts else ""

            if result.isError:
                return json.dumps({"error": combined or "MCP tool returned an error"})

            # Try to return as-is if it's valid JSON, else wrap it
            try:
                json.loads(combined)
                return combined
            except (json.JSONDecodeError, ValueError):
                return json.dumps({"result": combined})

        except Exception as exc:
            logger.warning("mcp_tool_call_failed", tool=self._tool_name, error=str(exc))
            return json.dumps({"error": f"MCP tool call failed: {exc}"})


class MCPClient:
    """Connects to MCP servers and discovers their tools."""

    def __init__(self) -> None:
        self._sessions: dict[str, Any] = {}  # server_name -> session

    async def connect(self, config: MCPServerConfig) -> list[MCPTool]:
        """Connect to an MCP server and discover its tools.

        Returns a list of MCPTool instances, or empty list on failure.
        """
        try:
            if config.transport == "http" and config.url:
                session = await self._connect_http(config)
            else:
                session = await self._connect_stdio(config)

            self._sessions[config.name] = session

            # Discover tools
            raw_tools = await session.list_tools()
            tools: list[MCPTool] = []
            for t in raw_tools:
                tool = MCPTool(
                    tool_name=t.name,
                    server_name=config.name,
                    tool_description=t.description or "",
                    tool_parameters=t.inputSchema if hasattr(t, "inputSchema") else {},
                    session=session,
                )
                tools.append(tool)

            logger.info(
                "mcp_tools_discovered",
                server=config.name,
                count=len(tools),
                tool_names=[t.name for t in tools],
            )
            return tools

        except Exception as exc:
            logger.warning(
                "mcp_connect_failed",
                server=config.name,
                error=str(exc),
            )
            return []

    async def _connect_stdio(self, config: MCPServerConfig) -> Any:
        """Connect via stdio transport (launches subprocess).

        Uses the `mcp` SDK if available, otherwise raises.
        """
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError as e:
            raise ImportError("MCP SDK not installed. Install with: uv add mcp") from e

        server_params = StdioServerParameters(
            command=config.command or "",
            args=config.args,
            env=config.env if config.env else None,
        )

        transport = await stdio_client(server_params).__aenter__()
        read_stream, write_stream = transport
        session = await ClientSession(read_stream, write_stream).__aenter__()
        await session.initialize()
        return session

    async def _connect_http(self, config: MCPServerConfig) -> Any:
        """Connect via HTTP/SSE transport."""
        try:
            from mcp import ClientSession
            from mcp.client.sse import sse_client
        except ImportError as e:
            raise ImportError("MCP SDK not installed. Install with: uv add mcp") from e

        transport = await sse_client(config.url or "").__aenter__()
        read_stream, write_stream = transport
        session = await ClientSession(read_stream, write_stream).__aenter__()
        await session.initialize()
        return session

    async def disconnect(self, server_name: str | None = None) -> None:
        """Disconnect from one or all MCP servers."""
        names = [server_name] if server_name else list(self._sessions.keys())
        for name in names:
            session = self._sessions.pop(name, None)
            if session and hasattr(session, "__aexit__"):
                import contextlib

                with contextlib.suppress(Exception):
                    await session.__aexit__(None, None, None)

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict[str, Any]) -> str:
        """Call a tool on a specific server by name."""
        session = self._sessions.get(server_name)
        if not session:
            return json.dumps({"error": f"No active session for server '{server_name}'"})

        temp_tool = MCPTool(tool_name, server_name, "", {}, session)
        return await temp_tool.execute(arguments)


async def load_mcp_servers(configs: list[dict[str, Any]]) -> list[MCPTool]:
    """Load tools from multiple MCP server configs.

    Failures for individual servers are logged but don't block others.
    Returns all successfully discovered tools.
    """
    all_tools: list[MCPTool] = []

    for raw_config in configs:
        try:
            config = MCPServerConfig.from_dict(raw_config)
            client = MCPClient()
            tools = await client.connect(config)
            all_tools.extend(tools)
        except Exception as exc:
            logger.warning(
                "mcp_load_server_failed",
                server=raw_config.get("name", "unknown"),
                error=str(exc),
            )

    logger.info("mcp_servers_loaded", total_tools=len(all_tools))
    return all_tools
