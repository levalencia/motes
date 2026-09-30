"""Memory routes: CRUD for persistent agent memory."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_session
from app.memory import Memory
from app.models import Agent, User

router = APIRouter(prefix="/api/agents/{agent_id}/memories", tags=["memory"])


class MemoryCreate(BaseModel):
    content: str = Field(min_length=1)
    category: str = "general"


class MemoryUpdate(BaseModel):
    content: str | None = None
    category: str | None = None


class MemoryResponse(BaseModel):
    id: str
    agent_id: str
    category: str
    content: str


async def _verify_agent_ownership(
    session: AsyncSession, agent_id: str, user_id: str
) -> Agent:
    """Verify the agent belongs to the user."""
    result = await session.execute(
        select(Agent).where(Agent.id == agent_id, Agent.user_id == user_id)
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("", response_model=MemoryResponse, status_code=201)
async def create_memory(
    agent_id: str,
    body: MemoryCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Add a memory entry to an agent."""
    await _verify_agent_ownership(session, agent_id, user.id)
    memory = Memory(
        id=str(uuid.uuid4()),
        agent_id=agent_id,
        content=body.content,
        category=body.category,
    )
    session.add(memory)
    await session.commit()
    await session.refresh(memory)
    return MemoryResponse(
        id=memory.id,
        agent_id=memory.agent_id,
        category=memory.category,
        content=memory.content,
    )


@router.get("", response_model=list[MemoryResponse])
async def list_memories(
    agent_id: str,
    category: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """List memories for an agent, optionally filtered by category."""
    await _verify_agent_ownership(session, agent_id, user.id)
    stmt = select(Memory).where(Memory.agent_id == agent_id)
    if category:
        stmt = stmt.where(Memory.category == category)
    stmt = stmt.order_by(Memory.created_at.desc())
    result = await session.execute(stmt)
    memories = result.scalars().all()
    return [
        MemoryResponse(
            id=m.id, agent_id=m.agent_id, category=m.category, content=m.content
        )
        for m in memories
    ]


@router.put("/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    agent_id: str,
    memory_id: str,
    body: MemoryUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Update a memory entry."""
    await _verify_agent_ownership(session, agent_id, user.id)
    result = await session.execute(
        select(Memory).where(Memory.id == memory_id, Memory.agent_id == agent_id)
    )
    memory = result.scalar_one_or_none()
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    if body.content is not None:
        memory.content = body.content
    if body.category is not None:
        memory.category = body.category
    await session.commit()
    await session.refresh(memory)
    return MemoryResponse(
        id=memory.id,
        agent_id=memory.agent_id,
        category=memory.category,
        content=memory.content,
    )


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(
    agent_id: str,
    memory_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Delete a memory entry."""
    await _verify_agent_ownership(session, agent_id, user.id)
    result = await session.execute(
        select(Memory).where(Memory.id == memory_id, Memory.agent_id == agent_id)
    )
    memory = result.scalar_one_or_none()
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    await session.delete(memory)
    await session.commit()


@router.get("/search", response_model=list[MemoryResponse])
async def search_memories(
    agent_id: str,
    q: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Search memories by content (case-insensitive substring match)."""
    await _verify_agent_ownership(session, agent_id, user.id)
    stmt = (
        select(Memory)
        .where(Memory.agent_id == agent_id, Memory.content.ilike(f"%{q}%"))
        .order_by(Memory.created_at.desc())
    )
    result = await session.execute(stmt)
    memories = result.scalars().all()
    return [
        MemoryResponse(
            id=m.id, agent_id=m.agent_id, category=m.category, content=m.content
        )
        for m in memories
    ]
