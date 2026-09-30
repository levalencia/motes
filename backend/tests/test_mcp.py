"""Tests for MCP connector management."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp_connector import (
    add_mcp_server,
    delete_mcp_server,
    get_catalog,
    list_mcp_servers,
    toggle_mcp_server,
)


@pytest.mark.unit
class TestMCPCatalog:
    """MCP server catalog tests."""

    def test_catalog_not_empty(self) -> None:
        catalog = get_catalog()
        assert len(catalog) > 0

    def test_catalog_has_gmail(self) -> None:
        catalog = get_catalog()
        names = [c["name"] for c in catalog]
        assert "Gmail" in names

    def test_catalog_has_calendar(self) -> None:
        catalog = get_catalog()
        names = [c["name"] for c in catalog]
        assert "Google Calendar" in names

    def test_catalog_entries_have_required_fields(self) -> None:
        catalog = get_catalog()
        for entry in catalog:
            assert "name" in entry
            assert "description" in entry
            assert "category" in entry


@pytest.mark.unit
class TestMCPServerCRUD:
    """MCP server CRUD tests."""

    @pytest.mark.asyncio
    async def test_add_server(self, session: AsyncSession) -> None:
        server = await add_mcp_server(
            session, "user-1", "Gmail", "Read emails",
            "stdio", "npx @anthropic/mcp-gmail", "",
        )
        assert server.name == "Gmail"
        assert server.is_enabled is True

    @pytest.mark.asyncio
    async def test_list_servers(self, session: AsyncSession) -> None:
        await add_mcp_server(
            session, "user-1", "Gmail", "", "stdio", "cmd1", ""
        )
        await add_mcp_server(
            session, "user-1", "Slack", "", "stdio", "cmd2", ""
        )
        servers = await list_mcp_servers(session, "user-1")
        assert len(servers) == 2

    @pytest.mark.asyncio
    async def test_toggle_server(self, session: AsyncSession) -> None:
        server = await add_mcp_server(
            session, "user-1", "Gmail", "", "stdio", "cmd", ""
        )
        toggled = await toggle_mcp_server(session, server.id, False)
        assert toggled is not None
        assert toggled.is_enabled is False

        re_enabled = await toggle_mcp_server(session, server.id, True)
        assert re_enabled is not None
        assert re_enabled.is_enabled is True

    @pytest.mark.asyncio
    async def test_delete_server(self, session: AsyncSession) -> None:
        server = await add_mcp_server(
            session, "user-1", "Gmail", "", "stdio", "cmd", ""
        )
        assert await delete_mcp_server(session, server.id, "user-1") is True
        assert await delete_mcp_server(session, server.id, "user-1") is False

    @pytest.mark.asyncio
    async def test_delete_wrong_user(self, session: AsyncSession) -> None:
        server = await add_mcp_server(
            session, "user-1", "Gmail", "", "stdio", "cmd", ""
        )
        assert await delete_mcp_server(session, server.id, "user-2") is False
