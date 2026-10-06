"""Persistent HTTP MCP proxy service.

Keeps HTTP MCP connections alive in the background using proper async context
managers (required by anyio TaskGroups in streamable_http_client).

Proxies tool calls from the agent loop through the persistent session.

Architecture:
    Chat → Agent Loop → MCPProxyTool.execute()
                               ↓
                        MCPProxyService (background task per server)
                               ↓
                        session.call_tool() → result
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.tools import Tool

logger = structlog.get_logger()

# Module-level singleton — survives hot reloads
_proxy_instance: MCPProxyService | None = None


def get_mcp_proxy() -> MCPProxyService:
    """Get or create the global MCP proxy service singleton."""
    global _proxy_instance
    if _proxy_instance is None:
        _proxy_instance = MCPProxyService()
    return _proxy_instance


@dataclass
class MCPConnection:
    """A live HTTP MCP connection with its discovered tools."""

    server_name: str
    url: str
    tools: dict[str, dict[str, Any]] = field(default_factory=dict)
    session: Any = None
    ready: bool = False
    _task: asyncio.Task | None = None


class MCPProxyService:
    """Background service managing persistent HTTP MCP connections."""

    def __init__(self) -> None:
        self._connections: dict[str, MCPConnection] = {}

    def is_connected(self, server_name: str) -> bool:
        conn = self._connections.get(server_name)
        return conn is not None and conn.ready

    def get_tool_schemas(self, server_name: str) -> dict[str, dict[str, Any]]:
        """Return discovered tool schemas for a connected server."""
        conn = self._connections.get(server_name)
        return conn.tools if conn else {}

    def all_tool_schemas(self) -> dict[str, dict[str, Any]]:
        """Return all tools across all connected servers, namespaced."""
        result: dict[str, dict[str, Any]] = {}
        for name, conn in self._connections.items():
            for tool_name, schema in conn.tools.items():
                result[f"mcp_{name}__{tool_name}"] = schema
        return result

    async def connect(self, server_name: str, url: str, timeout: float = 15.0) -> list[str]:
        """Connect to an HTTP MCP server. Returns list of tool names."""
        if self.is_connected(server_name):
            return list(self._connections[server_name].tools.keys())

        conn = MCPConnection(server_name=server_name, url=url)
        conn._task = asyncio.create_task(
            self._run_connection(conn),
            name=f"mcp_proxy_{server_name}",
        )

        # Wait for connection to establish
        elapsed = 0.0
        while elapsed < timeout:
            await asyncio.sleep(0.5)
            elapsed += 0.5
            if conn.ready:
                self._connections[server_name] = conn
                logger.info(
                    "mcp_proxy_connected",
                    server=server_name,
                    tools=len(conn.tools),
                )
                return list(conn.tools.keys())
            if conn._task.done():
                break

        logger.warning("mcp_proxy_connect_timeout", server=server_name)
        return []

    async def _run_connection(self, conn: MCPConnection) -> None:
        """Run a persistent MCP connection inside proper async with."""
        try:
            from mcp import ClientSession
            from mcp.client.streamable_http import streamable_http_client

            async with streamable_http_client(conn.url) as transport:  # noqa: SIM117
                async with ClientSession(transport[0], transport[1]) as session:
                    await session.initialize()
                    conn.session = session

                    # Discover tools
                    result = await session.list_tools()
                    logger.info("mcp_proxy_tools_raw", server=conn.server_name, count=len(result.tools))
                    for t in result.tools:
                        conn.tools[t.name] = {
                            "name": t.name,
                            "description": getattr(t, "description", "") or "",
                            "inputSchema": t.inputSchema if hasattr(t, "inputSchema") else {},
                        }

                    conn.ready = True

                    # Keep alive — wait forever until cancelled
                    try:
                        while True:
                            await asyncio.sleep(30)
                    except asyncio.CancelledError:
                        pass

        except asyncio.CancelledError:
            logger.info("mcp_proxy_disconnected", server=conn.server_name)
        except BaseException as exc:
            logger.warning("mcp_proxy_error", server=conn.server_name, error=str(exc))
        finally:
            conn.session = None

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool on a connected HTTP MCP server."""
        conn = self._connections.get(server_name)
        if not conn or not conn.session:
            return {"error": f"MCP server '{server_name}' not connected"}

        try:
            result = await conn.session.call_tool(tool_name, arguments=arguments)
            texts = []
            for item in result.content:
                if hasattr(item, "text"):
                    texts.append(item.text)
            return {"result": "\n".join(texts) if texts else str(result)}
        except BaseException as exc:
            logger.warning(
                "mcp_proxy_call_failed",
                server=server_name,
                tool=tool_name,
                error=str(exc),
            )
            return {"error": f"Tool call failed: {exc}"}

    async def disconnect(self, server_name: str | None = None) -> None:
        """Disconnect from one or all servers."""
        names = [server_name] if server_name else list(self._connections.keys())
        for name in names:
            conn = self._connections.pop(name, None)
            if conn and conn._task:
                conn._task.cancel()

    async def disconnect_all(self) -> None:
        """Disconnect all servers."""
        await self.disconnect()


class MCPProxyTool(Tool):
    """Tool that proxies calls through MCPProxyService for HTTP MCP servers."""

    def __init__(
        self,
        tool_name: str,
        server_name: str,
        tool_description: str,
        tool_parameters: dict[str, Any],
        proxy: MCPProxyService,
    ) -> None:
        self._tool_name = tool_name
        self._server_name = server_name
        self._description = tool_description
        self._parameters = tool_parameters
        self._proxy = proxy

    @property
    def name(self) -> str:
        safe = re.sub(r"[^a-zA-Z0-9]", "_", self._server_name).strip("_").lower()
        return f"mcp_{safe}__{self._tool_name}"

    @property
    def description(self) -> str:
        return self._description

    @property
    def parameters(self) -> dict[str, Any]:
        return self._parameters

    async def execute(self, arguments: dict[str, Any]) -> str:
        result = await self._proxy.call_tool(self._server_name, self._tool_name, arguments)
        return json.dumps(result)
