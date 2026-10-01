"""Agentic proactive intelligence.

Instead of hardcoded if/else, the LLM decides what to proactively
check based on conversation history, user patterns, and available tools.
Runs on a configurable interval (default: every hour).
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Agent, Message, Provider, User
from app.thread import get_or_create_thread

logger = structlog.get_logger()

PROACTIVE_SYSTEM_PROMPT = """You are Motes, an always-on AI assistant running a background check.
Review the conversation history and decide if there's anything useful to proactively tell the user RIGHT NOW.

Current time: {current_time}

Guidelines:
- Look at what the user recently asked about and provide a follow-up or update
- If they asked about weather → check if conditions changed or give a forecast update
- If they asked about news → share a new interesting headline they might have missed
- If they mentioned a meeting/event → remind them if it's coming up
- Check things relevant to their recent interests
- Keep it brief — one short message, 1-3 sentences
- Use the same language the user has been using in the thread
- Use tools to fetch fresh data when relevant

IMPORTANT: You MUST respond with something useful. Look at the conversation and find SOMETHING to proactively share. Only say __NOTHING__ if the thread is completely empty.
"""


async def run_agentic_proactive(
    session: AsyncSession,
    user: User,
    agent: Agent,
    provider: Provider,
    event_bus=None,
) -> str | None:
    """Run one proactive check cycle using the LLM with full tool access.

    Returns the proactive message if any, or None.
    """
    from app.memory import Memory
    from app.services import build_tool_registry

    # Skip if user disabled proactive
    if not getattr(user, "proactive_enabled", True):
        return None

    thread = await get_or_create_thread(session, agent.id)

    # Load recent thread messages for context
    msg_result = await session.execute(
        select(Message)
        .where(Message.conversation_id == thread.id)
        .order_by(Message.created_at.desc())
        .limit(20)
    )
    recent = list(reversed(msg_result.scalars().all()))

    # Load memories
    mem_result = await session.execute(
        select(Memory).where(Memory.agent_id == agent.id)
    )
    memories = mem_result.scalars().all()
    memory_context = ""
    if memories:
        memory_lines = [f"- [{m.category}] {m.content}" for m in memories]
        memory_context = "\n\nUser memories:\n" + "\n".join(memory_lines)

    # Build the proactive prompt
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    system = PROACTIVE_SYSTEM_PROMPT.format(current_time=now)
    system += memory_context
    system += "\n\n" + agent.system_prompt

    # Build message history
    messages = [{"role": "system", "content": system}]
    for m in recent:
        mt = getattr(m, "message_type", "chat")
        prefix = ""
        if mt == "call":
            prefix = "[voice call] "
        elif mt == "proactive":
            prefix = "[proactive] "
        elif mt == "system":
            continue  # Skip system markers
        messages.append({"role": m.role, "content": prefix + m.content})

    # Add the proactive trigger
    messages.append({
        "role": "user",
        "content": (
            "[SYSTEM: This is an automatic proactive check. "
            "Review the conversation and decide if there's anything useful "
            "to tell the user right now. Use tools if needed. "
            "If nothing is relevant, say __NOTHING__]"
        ),
    })

    # Build tool registry
    tool_registry = await build_tool_registry(session, user.id)

    # Run the agent with tools
    try:
        api_key = provider.api_key_encrypted  # stored as-is despite column name

        if getattr(provider, "api_format", "openai") == "anthropic":
            from app.agent_loop_anthropic import run_anthropic_stream

            response = ""
            async for event in run_anthropic_stream(
                base_url=provider.base_url,
                api_key=api_key,
                model=provider.model,
                messages=messages,
                tools=tool_registry,
                system_prompt=system,
                temperature=0.3,
                max_tokens=500,
            ):
                if event["type"] == "done":
                    response = event["content"]
                elif event["type"] == "error":
                    raise RuntimeError(event["message"])
        else:
            from app.agent_loop import run_agent_sync

            response = await run_agent_sync(
                base_url=provider.base_url,
                api_key=api_key,
                model=provider.model,
                messages=messages,
                tools=tool_registry,
                temperature=0.3,
                max_tokens=500,
            )
    except Exception as e:
        logger.warning("agentic_proactive_error", error=str(e))
        return None

    # Check if agent had something to say
    if not response or "__NOTHING__" in response:
        logger.debug("agentic_proactive_nothing")
        return None

    # Save to thread as proactive message
    session.add(Message(
        conversation_id=thread.id,
        role="assistant",
        content=response,
        message_type="proactive",
    ))
    await session.commit()

    # Publish to event bus for real-time push
    if event_bus is not None:
        from app.event_bus import ProactiveEvent

        await event_bus.publish(ProactiveEvent(
            user_id=user.id,
            agent_id=agent.id,
            title="💡 Motes",
            body=response[:300],
            category="proactive",
        ))

    logger.info(
        "agentic_proactive_sent",
        user_id=user.id,
        response_len=len(response),
    )
    return response
