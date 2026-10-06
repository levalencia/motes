"""Chat routes: conversations and streaming agent chat."""

from __future__ import annotations

import json

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.agent_loop import run_agent_stream
from app.dependencies import get_current_user, get_session
from app.models import Agent, Conversation, Message, Provider, User

logger = structlog.get_logger()

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: str | None = None


class ConversationResponse(BaseModel):
    id: str
    agent_id: str
    title: str
    conversation_type: str = "chat"
    updated_at: str | None = None


class ConversationRenameRequest(BaseModel):
    title: str


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    tool_name: str | None = None


@router.post("/agents/{agent_id}/chat")
async def chat(
    agent_id: str,
    body: ChatRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Send a message and get a streaming response via SSE."""
    # Load agent + provider
    result = await session.execute(select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    prov_result = await session.execute(select(Provider).where(Provider.id == agent.provider_id))
    provider = prov_result.scalar_one_or_none()
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Always use the single thread (Dots model)
    from app.thread import get_or_create_thread

    conversation = await get_or_create_thread(session, agent_id)

    # Save user message
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=body.message,
        message_type="chat",
    )
    session.add(user_msg)
    await session.commit()

    # Learn from this message (proactive intelligence)
    from app.proactive import learn_from_message

    await learn_from_message(session, user.id, agent_id, body.message)

    # Build message history with memory injection
    # Fetch agent memories to inject into system prompt
    from app.memory import Memory

    mem_result = await session.execute(
        select(Memory).where(Memory.agent_id == agent_id).order_by(Memory.created_at.desc()).limit(50)
    )
    memories = mem_result.scalars().all()
    memory_context = ""
    if memories:
        memory_lines = [f"- [{m.category}] {m.content}" for m in memories]
        memory_context = "\n\n## Your Memories\nYou have the following memories from past interactions:\n" + "\n".join(
            memory_lines
        )

    msg_result = await session.execute(
        select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at)
    )
    history = msg_result.scalars().all()

    messages = [{"role": "system", "content": agent.system_prompt + memory_context}]
    for msg in history:
        entry: dict = {"role": msg.role, "content": msg.content}
        if msg.tool_call_id:
            entry["tool_call_id"] = msg.tool_call_id
        messages.append(entry)

    # Build tool registry via service layer
    from app.services import build_tool_registry

    tools = await build_tool_registry(session, user.id, app_state=request.app.state)

    async def event_generator():
        full_content = ""
        try:
            # Pick the right agent loop based on provider API format
            if provider.api_format == "anthropic":
                from app.agent_loop_anthropic import run_anthropic_stream

                stream = run_anthropic_stream(
                    base_url=provider.base_url,
                    api_key=provider.api_key_encrypted,
                    model=provider.model,
                    messages=messages,
                    tools=tools,
                    system_prompt=agent.system_prompt + memory_context,
                    session=session,
                    agent_id=agent_id,
                )
            else:
                stream = run_agent_stream(
                    base_url=provider.base_url,
                    api_key=provider.api_key_encrypted,
                    model=provider.model,
                    messages=messages,
                    tools=tools,
                    session=session,
                    agent_id=agent_id,
                )

            async for event in stream:
                if event["type"] == "token":
                    full_content += event["content"]
                    yield {"event": "token", "data": json.dumps(event)}
                elif event["type"] in ("tool_call", "tool_result"):
                    yield {"event": event["type"], "data": json.dumps(event)}
                elif event["type"] == "approval_needed":
                    yield {"event": "approval_needed", "data": json.dumps(event)}
                elif event["type"] == "done":
                    full_content = event["content"]
                    yield {
                        "event": "done",
                        "data": json.dumps(
                            {
                                "type": "done",
                                "content": full_content,
                                "conversation_id": conversation.id,
                            }
                        ),
                    }
                elif event["type"] == "error":
                    yield {"event": "error", "data": json.dumps(event)}

            # Save assistant response
            if full_content:
                assistant_msg = Message(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=full_content,
                )
                session.add(assistant_msg)
                await session.commit()

        except Exception as exc:
            yield {"event": "error", "data": json.dumps({"type": "error", "message": str(exc)})}

    return EventSourceResponse(event_generator())


@router.get("/agents/{agent_id}/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    agent_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """List conversations for an agent."""
    # Verify agent belongs to user
    agent_result = await session.execute(select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id))
    if agent_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    result = await session.execute(
        select(Conversation).where(Conversation.agent_id == agent_id).order_by(Conversation.created_at.desc())
    )
    convos = result.scalars().all()
    return [
        ConversationResponse(
            id=c.id,
            agent_id=c.agent_id,
            title=c.title,
            conversation_type=getattr(c, "conversation_type", "chat"),
            updated_at=c.updated_at.isoformat() if getattr(c, "updated_at", None) else None,
        )
        for c in convos
    ]


@router.put("/conversations/{conversation_id}/rename")
async def rename_conversation(
    conversation_id: str,
    body: ConversationRenameRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Rename a conversation."""
    result = await session.execute(select(Conversation).where(Conversation.id == conversation_id))
    conv = result.scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv.title = body.title
    await session.commit()
    return {"id": conv.id, "title": conv.title}


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageResponse],
)
async def get_messages(
    conversation_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Get messages for a conversation."""
    # Verify conversation belongs to user's agent
    conv_result = await session.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = conv_result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    agent_result = await session.execute(
        select(Agent).where(Agent.id == conversation.agent_id, Agent.user_id == user.id)
    )
    if agent_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await session.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)
    )
    msgs = result.scalars().all()
    return [MessageResponse(id=m.id, role=m.role, content=m.content, tool_name=m.tool_name) for m in msgs]


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Delete a conversation and its messages."""
    result = await session.execute(select(Conversation).where(Conversation.id == conversation_id))
    conv = result.scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Verify agent belongs to user
    agent_result = await session.execute(select(Agent).where(Agent.id == conv.agent_id, Agent.user_id == user.id))
    if agent_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Delete messages first, then conversation
    await session.execute(delete(Message).where(Message.conversation_id == conversation_id))
    await session.delete(conv)
    await session.commit()
    return {"status": "ok"}


# ── Agent personality ──────────────────────────────────


class AgentPersonalityRequest(BaseModel):
    """Customize the agent's personality."""

    name: str = Field(default="", description="Display name")
    system_prompt: str = Field(default="", description="System prompt")
    language: str = Field(default="", description="Default language (e.g. Spanish, French)")


@router.get("/agents/{agent_id}/personality")
async def get_agent_personality(
    agent_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Get the agent's personality settings."""
    result = await session.execute(select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id))
    agent = result.scalars().first()
    if not agent:
        raise HTTPException(404, "Agent not found")
    return {
        "name": agent.name,
        "system_prompt": agent.system_prompt,
        "language": getattr(agent, "language", ""),
        "voice_personality": getattr(user, "voice_personality", ""),
    }


@router.put("/agents/{agent_id}/personality")
async def set_agent_personality(
    agent_id: str,
    body: AgentPersonalityRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Customize the agent's personality, name, and language."""
    result = await session.execute(select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id))
    agent = result.scalars().first()
    if not agent:
        raise HTTPException(404, "Agent not found")

    if body.name:
        agent.name = body.name
    if body.system_prompt:
        agent.system_prompt = body.system_prompt
    await session.commit()
    return {"status": "ok", "name": agent.name}


# ── Thread management (Dots model) ────────────────────


@router.get("/agents/{agent_id}/thread")
async def get_thread(
    agent_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Get the single thread for an agent with all messages."""
    from app.thread import get_or_create_thread

    thread = await get_or_create_thread(session, agent_id)
    result = await session.execute(
        select(Message).where(Message.conversation_id == thread.id).order_by(Message.created_at.asc())
    )
    messages = result.scalars().all()
    return {
        "thread_id": thread.id,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "message_type": m.message_type,
                "created_at": m.created_at.isoformat() if m.created_at else "",
            }
            for m in messages
        ],
    }


@router.delete("/agents/{agent_id}/thread")
async def clear_thread(
    agent_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Clear all messages in the thread (soft reset). Keeps the conversation."""
    from app.thread import get_or_create_thread

    thread = await get_or_create_thread(session, agent_id)
    await session.execute(delete(Message).where(Message.conversation_id == thread.id))
    await session.commit()
    return {"status": "ok", "cleared": True}


@router.delete("/agents/{agent_id}/reset")
async def reset_everything(
    agent_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Nuclear reset: delete ALL messages, conversations, memories, notifications."""
    from app.memory import Memory
    from app.proactive import Notification, UserPattern

    # Delete all messages in all conversations for this agent
    agent_result = await session.execute(select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id))
    agent = agent_result.scalars().first()
    if not agent:
        raise HTTPException(404, "Agent not found")

    # Delete messages
    convs = await session.execute(select(Conversation).where(Conversation.agent_id == agent_id))
    for conv in convs.scalars().all():
        await session.execute(delete(Message).where(Message.conversation_id == conv.id))
    # Delete conversations
    await session.execute(delete(Conversation).where(Conversation.agent_id == agent_id))
    # Delete memories
    await session.execute(delete(Memory).where(Memory.agent_id == agent_id))
    # Delete patterns and notifications
    await session.execute(delete(UserPattern).where(UserPattern.user_id == user.id))
    await session.execute(delete(Notification).where(Notification.user_id == user.id))
    await session.commit()
    logger.info("reset_everything", agent_id=agent_id, user_id=user.id)
    return {"status": "ok", "reset": True}
