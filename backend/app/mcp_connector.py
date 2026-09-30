"""MCP connector management — connect to external MCP servers for tools.

Motes connects to community MCP servers (e.g. Gmail, Google Calendar, GitHub)
which expose tools via the Model Context Protocol. Users configure which MCP
servers to connect to, and the tools become available to their agents.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class MCPServer(Base):
    """A configured MCP server connection."""

    __tablename__ = "mcp_servers"

    id: Mapped[str] = mapped_column(
        primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str]  # e.g. "Gmail", "Google Calendar"
    description: Mapped[str] = mapped_column(Text, default="")
    # Transport: "stdio" (local process) or "http" (remote SSE)
    transport: Mapped[str] = mapped_column(default="stdio")
    # For stdio: command to run (e.g. "npx @anthropic/mcp-gmail")
    command: Mapped[str] = mapped_column(default="")
    # For http: URL of the MCP server
    url: Mapped[str] = mapped_column(default="")
    # Environment variables (JSON) needed by the MCP server
    env_json: Mapped[str] = mapped_column(Text, default="{}")
    # Which agents can use this server (empty = all agents for this user)
    agent_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    is_enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# Well-known community MCP servers that users can install
MCP_SERVER_CATALOG: list[dict[str, Any]] = [
    {
        "name": "Gmail",
        "description": "Read, send, search, and label Gmail messages",
        "transport": "stdio",
        "command": "npx -y @anthropic/mcp-gmail",
        "env_vars": ["GMAIL_OAUTH_CLIENT_ID", "GMAIL_OAUTH_CLIENT_SECRET"],
        "category": "email",
    },
    {
        "name": "Google Calendar",
        "description": "Read, create, and update Google Calendar events",
        "transport": "stdio",
        "command": "npx -y @anthropic/mcp-google-calendar",
        "env_vars": ["GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET"],
        "category": "calendar",
    },
    {
        "name": "GitHub",
        "description": "Manage issues, PRs, repos, and notifications",
        "transport": "stdio",
        "command": "npx -y @modelcontextprotocol/server-github",
        "env_vars": ["GITHUB_PERSONAL_ACCESS_TOKEN"],
        "category": "development",
    },
    {
        "name": "Slack",
        "description": "Read and send Slack messages, manage channels",
        "transport": "stdio",
        "command": "npx -y @anthropic/mcp-slack",
        "env_vars": ["SLACK_BOT_TOKEN"],
        "category": "communication",
    },
    {
        "name": "Filesystem",
        "description": "Read and write files in a sandboxed directory",
        "transport": "stdio",
        "command": "npx -y @modelcontextprotocol/server-filesystem",
        "env_vars": [],
        "category": "utility",
    },
    {
        "name": "Web Search (Brave)",
        "description": "Search the web using Brave Search API",
        "transport": "stdio",
        "command": "npx -y @anthropic/mcp-brave-search",
        "env_vars": ["BRAVE_API_KEY"],
        "category": "search",
    },
]


async def add_mcp_server(
    session: AsyncSession,
    user_id: str,
    name: str,
    description: str,
    transport: str,
    command: str,
    url: str,
    env_json: str = "{}",
) -> MCPServer:
    """Add an MCP server configuration."""
    server = MCPServer(
        user_id=user_id,
        name=name,
        description=description,
        transport=transport,
        command=command,
        url=url,
        env_json=env_json,
    )
    session.add(server)
    await session.commit()
    await session.refresh(server)
    return server


async def list_mcp_servers(
    session: AsyncSession, user_id: str
) -> list[MCPServer]:
    """List MCP servers for a user."""
    result = await session.execute(
        select(MCPServer)
        .where(MCPServer.user_id == user_id)
        .order_by(MCPServer.created_at)
    )
    return list(result.scalars().all())


async def toggle_mcp_server(
    session: AsyncSession, server_id: str, enabled: bool
) -> MCPServer | None:
    """Enable or disable an MCP server."""
    result = await session.execute(
        select(MCPServer).where(MCPServer.id == server_id)
    )
    server = result.scalar_one_or_none()
    if server is None:
        return None
    server.is_enabled = enabled
    await session.commit()
    await session.refresh(server)
    return server


async def delete_mcp_server(
    session: AsyncSession, server_id: str, user_id: str
) -> bool:
    """Delete an MCP server config."""
    result = await session.execute(
        select(MCPServer).where(
            MCPServer.id == server_id, MCPServer.user_id == user_id
        )
    )
    server = result.scalar_one_or_none()
    if server is None:
        return False
    await session.delete(server)
    await session.commit()
    return True


def get_catalog() -> list[dict[str, Any]]:
    """Return the catalog of well-known MCP servers."""
    return MCP_SERVER_CATALOG
