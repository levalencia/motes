"""Incoming webhook routes for Slack and Telegram channels.

Users can message Motes FROM Slack/Telegram and get responses
in the same thread.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.app_settings import get_setting, set_setting
from app.dependencies import get_current_user, get_session
from app.models import Agent, Message, Provider, User
from app.thread import get_or_create_thread

logger = structlog.get_logger()

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

SLACK_API = "https://slack.com/api"
TELEGRAM_API = "https://api.telegram.org"


# ── Helpers ──────────────────────────────────────────────


def _verify_slack_signature(body: bytes, timestamp: str, signature: str) -> bool:
    """Verify Slack request signature using SLACK_SIGNING_SECRET."""
    secret = os.environ.get("SLACK_SIGNING_SECRET", "")
    if not secret:
        return False

    # Reject requests older than 5 minutes
    if abs(time.time() - int(timestamp)) > 300:
        return False

    sig_basestring = f"v0:{timestamp}:{body.decode()}"
    expected = "v0=" + hmac.new(
        secret.encode(), sig_basestring.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def _send_slack_reply(*, channel: str, text: str, thread_ts: str) -> None:
    """Post a reply back to a Slack thread."""
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        logger.warning("slack_reply_no_token")
        return

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{SLACK_API}/chat.postMessage",
            json={"channel": channel, "text": text, "thread_ts": thread_ts},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            },
        )
        if resp.status_code != 200:
            logger.warning("slack_reply_failed", status=resp.status_code)


async def _send_telegram_reply(*, chat_id: int, text: str, reply_to_message_id: int) -> None:
    """Send a reply back via Telegram Bot API."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        logger.warning("telegram_reply_no_token")
        return

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{TELEGRAM_API}/bot{bot_token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "reply_to_message_id": reply_to_message_id,
            },
        )
        if resp.status_code != 200:
            logger.warning("telegram_reply_failed", status=resp.status_code)


async def _run_agent_for_channel(
    session: AsyncSession,
    agent_id: str,
    user_text: str,
) -> str:
    """Run the agent loop for an incoming channel message and return the text response.

    This is a non-streaming version of the agent loop used for webhook responses.
    """
    # Load agent + provider
    result = await session.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return "Agent not found."

    prov_result = await session.execute(select(Provider).where(Provider.id == agent.provider_id))
    provider = prov_result.scalar_one_or_none()
    if not provider:
        return "Provider not configured."

    # Build message history
    conversation = await get_or_create_thread(session, agent_id)
    msg_result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
    )
    history = msg_result.scalars().all()

    # Build memory context
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

    messages = [{"role": "system", "content": agent.system_prompt + memory_context}]
    for msg in history:
        entry: dict = {"role": msg.role, "content": msg.content}
        if msg.tool_call_id:
            entry["tool_call_id"] = msg.tool_call_id
        messages.append(entry)

    # Build tools
    from app.services import build_tool_registry

    tools = await build_tool_registry(session, agent.user_id)

    # Run non-streaming agent loop
    full_content = ""
    try:
        if provider.api_format == "anthropic":
            from app.agent_loop_anthropic import run_anthropic_stream

            async for event in run_anthropic_stream(
                base_url=provider.base_url,
                api_key=provider.api_key_encrypted,
                model=provider.model,
                messages=messages,
                tools=tools,
                system_prompt=agent.system_prompt + memory_context,
            ):
                if event["type"] == "done":
                    full_content = event["content"]
                elif event["type"] == "token":
                    full_content += event["content"]
        else:
            from app.agent_loop import run_agent_stream

            async for event in run_agent_stream(
                base_url=provider.base_url,
                api_key=provider.api_key_encrypted,
                model=provider.model,
                messages=messages,
                tools=tools,
            ):
                if event["type"] == "done":
                    full_content = event["content"]
                elif event["type"] == "token":
                    full_content += event["content"]
    except Exception as e:
        logger.warning("channel_agent_error", error=str(e))
        full_content = "Sorry, I encountered an error processing your message."

    return full_content or "I didn't generate a response."


# ── Configuration endpoints ─────────────────────────────


class SlackConfigRequest(BaseModel):
    channel_id: str
    agent_id: str


class TelegramConfigRequest(BaseModel):
    chat_id: str
    agent_id: str


@router.post("/slack/config")
async def configure_slack_channel(
    body: SlackConfigRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Map a Slack channel to an agent."""
    # Verify agent belongs to user
    result = await session.execute(
        select(Agent).where(Agent.id == body.agent_id, Agent.user_id == user.id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    await set_setting(session, f"webhook:slack:channel:{body.channel_id}", body.agent_id)
    return {"status": "ok", "channel_id": body.channel_id, "agent_id": body.agent_id}


@router.post("/telegram/config")
async def configure_telegram_chat(
    body: TelegramConfigRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Map a Telegram chat to an agent."""
    result = await session.execute(
        select(Agent).where(Agent.id == body.agent_id, Agent.user_id == user.id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    await set_setting(session, f"webhook:telegram:chat:{body.chat_id}", body.agent_id)
    return {"status": "ok", "chat_id": body.chat_id, "agent_id": body.agent_id}


# ── Slack webhook ────────────────────────────────────────


@router.post("/slack")
async def slack_webhook(request: Request):
    """Receive Slack Events API callbacks.

    Handles:
    - url_verification: echo back challenge
    - event_callback with message: process and respond
    """
    body = await request.body()
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    if not _verify_slack_signature(body, timestamp, signature):
        raise HTTPException(status_code=403, detail="Invalid Slack signature")

    import json
    payload = json.loads(body)

    # URL verification challenge
    if payload.get("type") == "url_verification":
        return {"challenge": payload["challenge"]}

    # Event callback
    if payload.get("type") == "event_callback":
        event = payload.get("event", {})

        # Ignore bot messages to prevent loops
        if event.get("subtype") == "bot_message" or event.get("bot_id"):
            return {"status": "ignored"}

        if event.get("type") != "message" or not event.get("text"):
            return {"status": "ignored"}

        channel = event["channel"]
        text = event["text"]
        thread_ts = event.get("ts", "")

        # Get session from app state
        session_factory = request.app.state.session_factory
        async with session_factory() as session:
            # Look up agent for this channel
            agent_id = await get_setting(session, f"webhook:slack:channel:{channel}")
            if not agent_id:
                logger.warning("slack_no_agent_for_channel", channel=channel)
                return {"status": "ignored", "reason": "no_agent_mapping"}

            # Save incoming message to thread
            conversation = await get_or_create_thread(session, agent_id)
            user_msg = Message(
                conversation_id=conversation.id,
                role="user",
                content=text,
                message_type="slack",
            )
            session.add(user_msg)
            await session.commit()

            # Run agent
            response_text = await _run_agent_for_channel(session, agent_id, text)

            # Save assistant response
            assistant_msg = Message(
                conversation_id=conversation.id,
                role="assistant",
                content=response_text,
                message_type="slack",
            )
            session.add(assistant_msg)
            await session.commit()

        # Send reply back to Slack
        await _send_slack_reply(channel=channel, text=response_text, thread_ts=thread_ts)

        return {"status": "ok"}

    return {"status": "ignored"}


# ── Telegram webhook ─────────────────────────────────────


@router.post("/telegram")
async def telegram_webhook(request: Request):
    """Receive Telegram Bot API webhook updates.

    Processes text messages and responds via the same chat.
    """
    payload = await request.json()
    message = payload.get("message", {})

    if not message:
        return {"status": "ignored"}

    # Ignore bot messages
    from_user = message.get("from", {})
    if from_user.get("is_bot", False):
        return {"status": "ignored"}

    # Only handle text messages
    text = message.get("text")
    if not text:
        return {"status": "ignored"}

    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")

    if not chat_id:
        return {"status": "ignored"}

    # Get session from app state
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        # Look up agent for this chat
        agent_id = await get_setting(session, f"webhook:telegram:chat:{chat_id}")
        if not agent_id:
            logger.warning("telegram_no_agent_for_chat", chat_id=chat_id)
            return {"status": "ignored", "reason": "no_agent_mapping"}

        # Save incoming message to thread
        conversation = await get_or_create_thread(session, agent_id)
        user_msg = Message(
            conversation_id=conversation.id,
            role="user",
            content=text,
            message_type="telegram",
        )
        session.add(user_msg)
        await session.commit()

        # Run agent
        response_text = await _run_agent_for_channel(session, agent_id, text)

        # Save assistant response
        assistant_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=response_text,
            message_type="telegram",
        )
        session.add(assistant_msg)
        await session.commit()

    # Send reply back to Telegram
    await _send_telegram_reply(chat_id=chat_id, text=response_text, reply_to_message_id=message_id)

    return {"status": "ok"}
