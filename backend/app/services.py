"""Service layer for building tool registries.

Centralizes tool construction so routes don't have inline imports.
Used by chat, voice_call, and realtime_call routes via DI.
"""

from __future__ import annotations

import os
from pathlib import Path

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.file_tools import (
    FileDownloadUrlTool,
    FileListTool,
    FileReadTool,
    FileSearchTool,
    PptxAddSlideTool,
    PptxInspectTool,
)
from app.models import Agent
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

    # Weather (free, no API key — Open-Meteo)
    from app.weather_tool import WeatherTool

    tools.register(WeatherTool())

    # Memory (save/recall facts about the user)
    from app.memory_tools import MemoryRecallTool, MemorySaveTool

    agent_result = await session.execute(
        select(Agent).where(Agent.user_id == user_id)
    )
    agent_for_memory = agent_result.scalars().first()
    if agent_for_memory:
        tools.register(MemorySaveTool(session, agent_for_memory.id))
        tools.register(MemoryRecallTool(session, agent_for_memory.id))

    # Apple Reminders + Notes (macOS only, no API key)
    import platform

    if platform.system() == "Darwin":
        from app.apple_tools import (
            NotesListTool,
            NotesReadTool,
            ReminderCreateTool,
            ReminderListTool,
        )

        tools.register(ReminderListTool())
        tools.register(ReminderCreateTool())
        tools.register(NotesListTool())
        tools.register(NotesReadTool())
        logger.debug("tools_apple_loaded")

    # Maps (free, no API key — OpenStreetMap + OSRM)
    from app.maps_tool import MapsTool

    tools.register(MapsTool())

    # News (free, no API key — DuckDuckGo)
    from app.news_tool import NewsTool

    tools.register(NewsTool())

    # Travel (flights + hotels — requires Amadeus keys)
    amadeus_key = os.environ.get("AMADEUS_API_KEY", "")
    if amadeus_key:
        from app.travel_tools import FlightSearchTool, HotelSearchTool

        tools.register(FlightSearchTool())
        tools.register(HotelSearchTool())
        logger.debug("tools_travel_loaded")

    # GitHub (requires GITHUB_TOKEN)
    github_token = os.environ.get("GITHUB_TOKEN", "")
    if github_token:
        from app.github_tools import (
            GitHubCreateIssueTool,
            GitHubListIssuesTool,
            GitHubListReposTool,
        )

        tools.register(GitHubListReposTool())
        tools.register(GitHubListIssuesTool())
        tools.register(GitHubCreateIssueTool())
        logger.debug("tools_github_loaded")

    # Todoist (requires TODOIST_API_KEY)
    todoist_key = os.environ.get("TODOIST_API_KEY", "")
    if todoist_key:
        from app.todoist_tools import TodoistCreateTool, TodoistListTool

        tools.register(TodoistListTool())
        tools.register(TodoistCreateTool())
        logger.debug("tools_todoist_loaded")

    # Notion (requires NOTION_API_KEY)
    notion_key = os.environ.get("NOTION_API_KEY", "")
    if notion_key:
        from app.notion_tools import NotionReadPageTool, NotionSearchTool

        tools.register(NotionSearchTool())
        tools.register(NotionReadPageTool())
        logger.debug("tools_notion_loaded")

    # Slack (requires SLACK_BOT_TOKEN)
    slack_token = os.environ.get("SLACK_BOT_TOKEN", "")
    if slack_token:
        from app.slack_tools import (
            SlackListChannelsTool,
            SlackReadMessagesTool,
            SlackSendMessageTool,
        )

        tools.register(SlackListChannelsTool())
        tools.register(SlackSendMessageTool())
        tools.register(SlackReadMessagesTool())
        logger.debug("tools_slack_loaded")

    # Spotify (requires SPOTIFY_TOKEN)
    spotify_token = os.environ.get("SPOTIFY_TOKEN", "")
    if spotify_token:
        from app.spotify_tools import SpotifyPlayTool, SpotifySearchTool

        tools.register(SpotifySearchTool())
        tools.register(SpotifyPlayTool())
        logger.debug("tools_spotify_loaded")

    # Home Assistant (requires HA_URL + HA_TOKEN)
    ha_url = os.environ.get("HA_URL", "")
    if ha_url:
        from app.homeassistant_tools import HAControlDeviceTool, HAListDevicesTool

        tools.register(HAListDevicesTool())
        tools.register(HAControlDeviceTool())
        logger.debug("tools_homeassistant_loaded")

    # Outlook (requires OUTLOOK_ACCESS_TOKEN)
    outlook_token = os.environ.get("OUTLOOK_ACCESS_TOKEN", "")
    if outlook_token:
        from app.outlook_tools import (
            OutlookCalendarTool,
            OutlookReadEmailTool,
            OutlookSendEmailTool,
        )

        tools.register(OutlookReadEmailTool())
        tools.register(OutlookSendEmailTool())
        tools.register(OutlookCalendarTool())
        logger.debug("tools_outlook_loaded")

    # Telegram (requires TELEGRAM_BOT_TOKEN)
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if telegram_token:
        from app.messaging_tools import TelegramSendTool

        tools.register(TelegramSendTool())
        logger.debug("tools_telegram_loaded")

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
