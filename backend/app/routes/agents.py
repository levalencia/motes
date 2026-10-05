"""Agent routes: create, list, delete agents."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_session
from app.models import Agent, Provider, User

router = APIRouter(prefix="/api/agents", tags=["agents"])


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    provider_id: str
    system_prompt: str = "You are a helpful assistant."


class AgentResponse(BaseModel):
    id: str
    name: str
    provider_id: str
    system_prompt: str
    provider_name: str | None = None
    model: str | None = None


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(
    body: AgentCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Create a new agent."""
    # Verify provider belongs to user
    result = await session.execute(select(Provider).where(Provider.id == body.provider_id, Provider.user_id == user.id))
    provider = result.scalar_one_or_none()
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")

    agent = Agent(
        user_id=user.id,
        provider_id=body.provider_id,
        name=body.name,
        system_prompt=body.system_prompt,
    )
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        provider_id=agent.provider_id,
        system_prompt=agent.system_prompt,
        provider_name=provider.name,
        model=provider.model,
    )


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """List all agents for the current user."""
    result = await session.execute(select(Agent).where(Agent.user_id == user.id).order_by(Agent.created_at))
    agents = result.scalars().all()
    response = []
    for agent in agents:
        # Eager-load provider info
        stmt = select(Provider).where(Provider.id == agent.provider_id)
        prov_result = await session.execute(stmt)
        prov = prov_result.scalar_one_or_none()
        response.append(
            AgentResponse(
                id=agent.id,
                name=agent.name,
                provider_id=agent.provider_id,
                system_prompt=agent.system_prompt,
                provider_name=prov.name if prov else None,
                model=prov.model if prov else None,
            )
        )
    return response


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Delete an agent."""
    result = await session.execute(select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    await session.delete(agent)
    await session.commit()
