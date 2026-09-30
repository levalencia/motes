"""Chat routes: conversations and streaming agent chat."""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.agent_loop import run_agent_stream
from app.dependencies import get_current_user, get_session
from app.models import Agent, Conversation, Message, Provider, User
from app.tools import create_default_registry

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: str | None = None


class ConversationResponse(BaseModel):
    id: str
    agent_id: str
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
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Send a message and get a streaming response via SSE."""
    # Load agent + provider
    result = await session.execute(
        select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id)
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    prov_result = await session.execute(
        select(Provider).where(Provider.id == agent.provider_id)
    )
    provider = prov_result.scalar_one_or_none()
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Get or create conversation
    if body.conversation_id:
        conv_result = await session.execute(
            select(Conversation).where(
                Conversation.id == body.conversation_id,
                Conversation.agent_id == agent_id,
            )
        )
        conversation = conv_result.scalar_one_or_none()
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation = Conversation(agent_id=agent_id, title=body.message[:100])
        session.add(conversation)
        await session.commit()
        await session.refresh(conversation)

    # Save user message
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=body.message,
    )
    session.add(user_msg)
    await session.commit()

    # Build message history with memory injection
    # Fetch agent memories to inject into system prompt
    from app.memory import Memory

    mem_result = await session.execute(
        select(Memory)
        .where(Memory.agent_id == agent_id)
        .order_by(Memory.created_at.desc())
        .limit(50)
    )
    memories = mem_result.scalars().all()
    memory_context = ""
    if memories:
        memory_lines = [f"- [{m.category}] {m.content}" for m in memories]
        memory_context = (
            "\n\n## Your Memories\n"
            "You have the following memories from past interactions:\n"
            + "\n".join(memory_lines)
        )

    msg_result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
    )
    history = msg_result.scalars().all()

    messages = [{"role": "system", "content": agent.system_prompt + memory_context}]
    for msg in history:
        entry: dict = {"role": msg.role, "content": msg.content}
        if msg.tool_call_id:
            entry["tool_call_id"] = msg.tool_call_id
        messages.append(entry)

    # Create tool registry with built-in + connected service tools
    tools = create_default_registry()

    # Load file tools (local computer access)
    from app.file_tools import (
        FileDownloadUrlTool,
        FileListTool,
        FileReadTool,
        FileSearchTool,
        PptxAddSlideTool,
        PptxInspectTool,
    )

    home_dir = str(Path.home())
    tools.register(FileListTool(home_dir))
    tools.register(FileReadTool(home_dir))
    tools.register(FileSearchTool(home_dir))
    tools.register(PptxInspectTool(home_dir))
    tools.register(PptxAddSlideTool(home_dir))
    tools.register(FileDownloadUrlTool(home_dir))

    # Web search tool (free DuckDuckGo fallback, Brave if key configured)
    from app.web_search_tool import WebSearchTool

    brave_key = os.environ.get("BRAVE_SEARCH_API_KEY", "")
    tools.register(WebSearchTool(brave_key))

    # Load Google tools if user has connected Gmail/Calendar
    from app.oauth import OAuthToken

    gmail_token_result = await session.execute(
        select(OAuthToken).where(
            OAuthToken.user_id == user.id,
            OAuthToken.service == "gmail",
        )
    )
    gmail_token = gmail_token_result.scalar_one_or_none()
    if gmail_token:
        from app.google_tools import GmailReadTool, GmailSendTool

        tools.register(GmailReadTool(gmail_token.access_token_encrypted))
        tools.register(GmailSendTool(gmail_token.access_token_encrypted))

    calendar_token_result = await session.execute(
        select(OAuthToken).where(
            OAuthToken.user_id == user.id,
            OAuthToken.service == "calendar",
        )
    )
    calendar_token = calendar_token_result.scalar_one_or_none()
    if calendar_token:
        from app.google_tools import CalendarCreateTool, CalendarListTool

        tools.register(CalendarListTool(calendar_token.access_token_encrypted))
        tools.register(CalendarCreateTool(calendar_token.access_token_encrypted))

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
                )
            else:
                stream = run_agent_stream(
                    base_url=provider.base_url,
                    api_key=provider.api_key_encrypted,
                    model=provider.model,
                    messages=messages,
                    tools=tools,
                )

            async for event in stream:
                if event["type"] == "token":
                    full_content += event["content"]
                    yield {"event": "token", "data": json.dumps(event)}
                elif event["type"] in ("tool_call", "tool_result"):
                    yield {"event": event["type"], "data": json.dumps(event)}
                elif event["type"] == "done":
                    full_content = event["content"]
                    yield {"event": "done", "data": json.dumps({
                        "type": "done",
                        "content": full_content,
                        "conversation_id": conversation.id,
                    })}
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
    agent_result = await session.execute(
        select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id)
    )
    if agent_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    result = await session.execute(
        select(Conversation)
        .where(Conversation.agent_id == agent_id)
        .order_by(Conversation.created_at.desc())
    )
    convos = result.scalars().all()
    return [
        ConversationResponse(id=c.id, agent_id=c.agent_id, title=c.title)
        for c in convos
    ]


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
    conv_result = await session.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = conv_result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    agent_result = await session.execute(
        select(Agent).where(Agent.id == conversation.agent_id, Agent.user_id == user.id)
    )
    if agent_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    msgs = result.scalars().all()
    return [
        MessageResponse(id=m.id, role=m.role, content=m.content, tool_name=m.tool_name)
        for m in msgs
    ]
