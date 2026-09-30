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
    # ── Built-in (no API key needed) ──
    {
        "name": "Gmail",
        "description": "Read, send, and search Gmail messages",
        "category": "email",
        "built_in": True,
        "requires_oauth": True,
    },
    {
        "name": "Google Calendar",
        "description": "View and create Google Calendar events",
        "category": "calendar",
        "built_in": True,
        "requires_oauth": True,
    },
    {
        "name": "Weather",
        "description": "Current weather and 7-day forecast for any city (free)",
        "category": "utility",
        "built_in": True,
    },
    {
        "name": "Web Search",
        "description": "Search the web via DuckDuckGo (free) or Brave",
        "category": "search",
        "built_in": True,
    },
    {
        "name": "Apple Reminders",
        "description": "List and create reminders on macOS",
        "category": "productivity",
        "built_in": True,
        "macos_only": True,
    },
    {
        "name": "Apple Notes",
        "description": "Read and list notes on macOS",
        "category": "productivity",
        "built_in": True,
        "macos_only": True,
    },
    {
        "name": "Maps & Directions",
        "description": "Search places, get directions via OpenStreetMap (free)",
        "category": "utility",
        "built_in": True,
    },
    {
        "name": "News",
        "description": "Search latest news on any topic (free)",
        "category": "information",
        "built_in": True,
    },
    {
        "name": "Local Files",
        "description": "Browse, read, search files on your computer",
        "category": "utility",
        "built_in": True,
    },
    # ── Requires API key (set in environment) ──
    {
        "name": "GitHub",
        "description": "List repos, issues, create issues",
        "category": "development",
        "env_vars": ["GITHUB_TOKEN"],
    },
    {
        "name": "Slack",
        "description": "Read and send Slack messages",
        "category": "communication",
        "env_vars": ["SLACK_BOT_TOKEN"],
    },
    {
        "name": "Todoist",
        "description": "Manage tasks and projects",
        "category": "productivity",
        "env_vars": ["TODOIST_API_KEY"],
    },
    {
        "name": "Notion",
        "description": "Search and read Notion pages",
        "category": "productivity",
        "env_vars": ["NOTION_API_KEY"],
    },
    {
        "name": "Spotify",
        "description": "Search music, control playback",
        "category": "entertainment",
        "env_vars": ["SPOTIFY_TOKEN"],
    },
    {
        "name": "Home Assistant",
        "description": "Control smart home devices",
        "category": "smart_home",
        "env_vars": ["HA_URL", "HA_TOKEN"],
    },
    {
        "name": "Outlook / Office 365",
        "description": "Read/send emails, calendar via Microsoft Graph",
        "category": "email",
        "env_vars": ["OUTLOOK_ACCESS_TOKEN"],
    },
    {
        "name": "Flights & Hotels",
        "description": "Search flights and hotels (Amadeus API)",
        "category": "travel",
        "env_vars": ["AMADEUS_API_KEY", "AMADEUS_API_SECRET"],
    },
    {
        "name": "Telegram",
        "description": "Send messages via Telegram bot",
        "category": "communication",
        "env_vars": ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"],
    },
    {
        "name": "Google Drive",
        "description": "Access and search Google Drive files",
        "category": "storage",
        "requires_oauth": True,
        "coming_soon": True,
    },
    {
        "name": "WhatsApp",
        "description": "Send and receive WhatsApp messages",
        "category": "communication",
        "coming_soon": True,
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
