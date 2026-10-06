"""Service layer for building tool registries.

Centralizes tool construction so routes don't have inline imports.
Used by chat, voice_call, and realtime_call routes via DI.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

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


async def build_tool_registry(session: AsyncSession, user_id: str, app_state: Any = None) -> ToolRegistry:
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

    agent_result = await session.execute(select(Agent).where(Agent.user_id == user_id))
    agent_for_memory = agent_result.scalars().first()
    if agent_for_memory:
        tools.register(MemorySaveTool(session, agent_for_memory.id))
        tools.register(MemoryRecallTool(session, agent_for_memory.id))

    # Scheduled tasks tool
    from app.task_tools import ScheduledTasksTool

    if agent_for_memory:
        tools.register(ScheduledTasksTool(session, agent_for_memory.id))

    # Vision tool — image analysis using the provider's model
    from app.vision_tool import VisionTool

    provider_result = await session.execute(select(Agent).where(Agent.user_id == user_id).limit(1))
    agent_for_vision = provider_result.scalars().first()
    if agent_for_vision:
        from app.models import Provider

        prov_result = await session.execute(select(Provider).where(Provider.id == agent_for_vision.provider_id))
        prov = prov_result.scalars().first()
        if prov:
            tools.register(
                VisionTool(
                    provider_url=prov.base_url,
                    api_key=prov.api_key_encrypted,
                    model=prov.model,
                    api_format=getattr(prov, "api_format", "openai"),
                )
            )

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

    # MCP servers (user-configured external tool servers)
    from app.mcp_client import MCPClient, MCPServerConfig
    from app.mcp_connector import list_mcp_servers as list_mcp_configs
    from app.mcp_proxy import MCPProxyTool

    try:
        import json as json_mod

        # Get proxy service singleton
        from app.mcp_proxy import get_mcp_proxy

        mcp_proxy = get_mcp_proxy()

        mcp_servers = await list_mcp_configs(session, user_id)
        for srv in mcp_servers:
            if not srv.is_enabled:
                continue
            try:
                proxy_connected = mcp_proxy.is_connected(srv.name.strip())
                if proxy_connected:
                    schemas = mcp_proxy.get_tool_schemas(srv.name.strip())
                    for tool_name, schema in schemas.items():
                        params = schema.get("inputSchema", {})
                        if not params or "type" not in params:
                            params = {"type": "object", "properties": {}}
                        tool = MCPProxyTool(
                            tool_name=tool_name,
                            server_name=srv.name.strip(),
                            tool_description=schema.get("description", ""),
                            tool_parameters=params,
                            proxy=mcp_proxy,
                        )
                        tools.register(tool)
                    if schemas:
                        logger.info("tools_mcp_loaded", server=srv.name, count=len(schemas))
                    continue

                # Stdio MCP — direct connection with timeout
                env = json_mod.loads(srv.env_json) if srv.env_json else {}
                config = MCPServerConfig(
                    name=srv.name,
                    command=srv.command or None,
                    args=srv.command.split()[1:] if srv.command and " " in srv.command else [],
                    env=env,
                    url=srv.url or None,
                    transport=srv.transport,
                )
                client = MCPClient()
                try:
                    mcp_tools = await asyncio.wait_for(client.connect(config), timeout=10.0)
                except TimeoutError:
                    logger.warning("mcp_server_load_timeout", server=srv.name)
                    mcp_tools = []
                for mt in mcp_tools:
                    tools.register(mt)
                if mcp_tools:
                    logger.debug("tools_mcp_loaded", server=srv.name, count=len(mcp_tools))
            except BaseException as exc:
                logger.warning("mcp_server_load_failed", server=srv.name, error=str(exc))
    except BaseException as exc:
        logger.warning("mcp_servers_load_failed", error=str(exc))

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
