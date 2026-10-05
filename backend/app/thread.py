"""Thread management — single conversation per agent (Dots model).

Every agent has ONE conversation thread. Chat, calls, and proactive
notifications all go into the same thread.
"""

from __future__ import annotations

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Conversation

logger = structlog.get_logger()


async def get_or_create_thread(
    session: AsyncSession,
    agent_id: str,
) -> Conversation:
    """Get the single thread for an agent, or create it.

    In the Dots model, each agent has exactly ONE conversation.
    All messages (chat, call transcripts, proactive) go here.
    """
    result = await session.execute(
        select(Conversation).where(Conversation.agent_id == agent_id).order_by(Conversation.created_at.asc()).limit(1)
    )
    thread = result.scalars().first()

    if thread:
        return thread

    # Create the single thread
    thread = Conversation(
        agent_id=agent_id,
        title="Motes",
        conversation_type="thread",
    )
    session.add(thread)
    await session.commit()
    await session.refresh(thread)
    logger.info("thread_created", agent_id=agent_id, thread_id=thread.id)
    return thread
