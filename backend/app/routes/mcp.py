"""MCP connector routes: server management and catalog."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_session
from app.mcp_connector import (
    add_mcp_server,
    delete_mcp_server,
    get_catalog,
    list_mcp_servers,
    toggle_mcp_server,
)
from app.models import User

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


class MCPServerCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""
    transport: str = "stdio"
    command: str = ""
    url: str = ""
    env_json: str = "{}"


class MCPServerResponse(BaseModel):
    id: str
    name: str
    description: str
    transport: str
    command: str
    url: str
    is_enabled: bool


class MCPCatalogEntry(BaseModel):
    name: str
    description: str
    category: str
    built_in: bool = False
    requires_oauth: bool = False
    macos_only: bool = False
    env_vars: list[str] = []
    coming_soon: bool = False


@router.get("/catalog", response_model=list[MCPCatalogEntry])
async def catalog():
    """Get the catalog of well-known MCP servers."""
    return get_catalog()


@router.post("/servers", response_model=MCPServerResponse, status_code=201)
async def create_server(
    body: MCPServerCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Add an MCP server configuration."""
    server = await add_mcp_server(
        session, user.id, body.name, body.description,
        body.transport, body.command, body.url, body.env_json,
    )
    return MCPServerResponse(
        id=server.id, name=server.name, description=server.description,
        transport=server.transport, command=server.command,
        url=server.url, is_enabled=server.is_enabled,
    )


@router.get("/servers", response_model=list[MCPServerResponse])
async def get_servers(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """List configured MCP servers."""
    servers = await list_mcp_servers(session, user.id)
    return [
        MCPServerResponse(
            id=s.id, name=s.name, description=s.description,
            transport=s.transport, command=s.command,
            url=s.url, is_enabled=s.is_enabled,
        )
        for s in servers
    ]


@router.post("/servers/{server_id}/toggle", response_model=MCPServerResponse)
async def toggle(
    server_id: str,
    enabled: bool = True,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Enable or disable an MCP server."""
    server = await toggle_mcp_server(session, server_id, enabled)
    if server is None:
        raise HTTPException(status_code=404, detail="Server not found")
    return MCPServerResponse(
        id=server.id, name=server.name, description=server.description,
        transport=server.transport, command=server.command,
        url=server.url, is_enabled=server.is_enabled,
    )


@router.delete("/servers/{server_id}", status_code=204)
async def remove_server(
    server_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Delete an MCP server configuration."""
    deleted = await delete_mcp_server(session, server_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Server not found")


class MCPTestResult(BaseModel):
    success: bool
    tools_discovered: int = 0
    tool_names: list[str] = []
    error: str = ""


@router.post("/servers/{server_id}/test", response_model=MCPTestResult)
async def test_server_connection(
    server_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Test connection to an MCP server and discover its tools."""
    import json as json_mod

    from sqlalchemy import select

    from app.mcp_client import MCPClient, MCPServerConfig
    from app.mcp_connector import MCPServer

    result = await session.execute(
        select(MCPServer).where(MCPServer.id == server_id, MCPServer.user_id == user.id)
    )
    server = result.scalar_one_or_none()
    if server is None:
        raise HTTPException(status_code=404, detail="Server not found")

    try:
        env = json_mod.loads(server.env_json) if server.env_json else {}
        config = MCPServerConfig(
            name=server.name,
            command=server.command or None,
            args=server.command.split()[1:] if server.command and " " in server.command else [],
            env=env,
            url=server.url or None,
            transport=server.transport,
        )
        client = MCPClient()
        tools = await client.connect(config)
        await client.disconnect()

        return MCPTestResult(
            success=True,
            tools_discovered=len(tools),
            tool_names=[t.name for t in tools],
        )
    except Exception as exc:
        return MCPTestResult(success=False, error=str(exc))
