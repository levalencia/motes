"""Service layer for building tool registries.

Centralizes tool construction so routes don't have inline imports.
Used by chat, voice_call, and realtime_call routes via DI.
"""

from __future__ import annotations

import os
from pathlib import Path

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.file_tools import (
    FileDownloadUrlTool,
    FileListTool,
    FileReadTool,
    FileSearchTool,
    PptxAddSlideTool,
    PptxInspectTool,
)
from app.token_refresh import get_valid_token
from app.tools import ToolRegistry, create_default_registry
from app.web_search_tool import WebSearchTool

logger = structlog.get_logger()


async def build_tool_registry(
    session: AsyncSession, user_id: str
) -> ToolRegistry:
    """Build a complete tool registry with all available tools.

    Includes: built-in tools, file tools, web search, and
    Google tools (Gmail/Calendar) if the user has connected them.
    """
    tools = create_default_registry()

    # File tools (always available)
    home_dir = str(Path.home())
    tools.register(FileListTool(home_dir))
    tools.register(FileReadTool(home_dir))
    tools.register(FileSearchTool(home_dir))
    tools.register(PptxInspectTool(home_dir))
    tools.register(PptxAddSlideTool(home_dir))
    tools.register(FileDownloadUrlTool(home_dir))

    # Web search (DuckDuckGo free fallback, Brave if key configured)
    brave_key = os.environ.get("BRAVE_SEARCH_API_KEY", "")
    tools.register(WebSearchTool(brave_key))

    # Gmail (if connected, with auto-refresh)
    gmail_access = await get_valid_token(session, user_id, "gmail")
    if gmail_access:
        from app.google_tools import GmailReadTool, GmailSendTool

        tools.register(GmailReadTool(gmail_access))
        tools.register(GmailSendTool(gmail_access))
        logger.debug("tools_gmail_loaded", user_id=user_id)

    # Calendar (if connected, with auto-refresh)
    calendar_access = await get_valid_token(session, user_id, "calendar")
    if calendar_access:
        from app.google_tools import CalendarCreateTool, CalendarListTool

        tools.register(CalendarListTool(calendar_access))
        tools.register(CalendarCreateTool(calendar_access))
        logger.debug("tools_calendar_loaded", user_id=user_id)

    return tools
