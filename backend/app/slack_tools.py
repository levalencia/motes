"""Slack tools — list channels, send and read messages via Slack Web API.

Uses SLACK_BOT_TOKEN env var for authentication.
"""

from __future__ import annotations

import json
import os

import httpx
import structlog

from app.tools import Tool

logger = structlog.get_logger()

SLACK_API = "https://slack.com/api"


def _slack_headers() -> dict[str, str]:
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }


class SlackListChannelsTool(Tool):
    """List Slack channels the bot has access to."""

    name = "slack_list_channels"
    description = (
        "List Slack channels in the workspace that the bot can see. "
        "Returns channel names, IDs, topics, and member counts. "
        "Requires SLACK_BOT_TOKEN env var."
    )
    parameters = {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Max channels to return (default: 20)",
            },
            "types": {
                "type": "string",
                "description": "Channel types: 'public_channel', 'private_channel' (default: public_channel)",
            },
        },
        "required": [],
    }

    async def execute(self, arguments: dict) -> str:
        limit = arguments.get("limit", 20)
        types = arguments.get("types", "public_channel")

        if not os.environ.get("SLACK_BOT_TOKEN"):
            return json.dumps({"error": "SLACK_BOT_TOKEN env var is required"})

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{SLACK_API}/conversations.list",
                    params={"types": types, "limit": limit, "exclude_archived": True},
                    headers=_slack_headers(),
                )
                resp.raise_for_status()
                data = resp.json()

                if not data.get("ok"):
                    return json.dumps({"error": data.get("error", "Unknown Slack error")})

                channels = []
                for ch in data.get("channels", [])[:limit]:
                    channels.append(
                        {
                            "id": ch.get("id"),
                            "name": ch.get("name"),
                            "topic": ch.get("topic", {}).get("value", ""),
                            "purpose": ch.get("purpose", {}).get("value", ""),
                            "num_members": ch.get("num_members"),
                            "is_private": ch.get("is_private"),
                        }
                    )
                return json.dumps({"channels": channels, "count": len(channels)})
        except Exception as e:
            logger.warning("slack_list_channels_error", error=str(e))
            return json.dumps({"error": str(e)})


class SlackSendMessageTool(Tool):
    """Send a message to a Slack channel."""

    name = "slack_send_message"
    description = (
        "Send a message to a Slack channel. "
        "Supports plain text and basic Slack markdown formatting. "
        "Requires SLACK_BOT_TOKEN env var with chat:write scope."
    )
    parameters = {
        "type": "object",
        "properties": {
            "channel": {
                "type": "string",
                "description": "Channel ID or name (e.g., 'C01234ABCDE' or '#general')",
            },
            "text": {
                "type": "string",
                "description": "Message text to send",
            },
            "thread_ts": {
                "type": "string",
                "description": "Thread timestamp to reply in a thread (optional)",
            },
        },
        "required": ["channel", "text"],
    }

    async def execute(self, arguments: dict) -> str:
        channel = arguments.get("channel", "")
        text = arguments.get("text", "")
        thread_ts = arguments.get("thread_ts")

        if not channel or not text:
            return json.dumps({"error": "channel and text are required"})
        if not os.environ.get("SLACK_BOT_TOKEN"):
            return json.dumps({"error": "SLACK_BOT_TOKEN env var is required"})

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                payload = {"channel": channel, "text": text}
                if thread_ts:
                    payload["thread_ts"] = thread_ts

                resp = await client.post(
                    f"{SLACK_API}/chat.postMessage",
                    json=payload,
                    headers=_slack_headers(),
                )
                resp.raise_for_status()
                data = resp.json()

                if not data.get("ok"):
                    return json.dumps({"error": data.get("error", "Unknown Slack error")})

                return json.dumps(
                    {
                        "sent": True,
                        "channel": data.get("channel"),
                        "ts": data.get("ts"),
                        "message": data.get("message", {}).get("text"),
                    }
                )
        except Exception as e:
            logger.warning("slack_send_message_error", error=str(e))
            return json.dumps({"error": str(e)})


class SlackReadMessagesTool(Tool):
    """Read recent messages from a Slack channel."""

    name = "slack_read_messages"
    description = (
        "Read recent messages from a Slack channel. "
        "Returns message text, authors, and timestamps. "
        "Requires SLACK_BOT_TOKEN env var with channels:history scope."
    )
    parameters = {
        "type": "object",
        "properties": {
            "channel": {
                "type": "string",
                "description": "Channel ID (e.g., 'C01234ABCDE')",
            },
            "limit": {
                "type": "integer",
                "description": "Max messages to return (default: 10)",
            },
        },
        "required": ["channel"],
    }

    async def execute(self, arguments: dict) -> str:
        channel = arguments.get("channel", "")
        limit = arguments.get("limit", 10)

        if not channel:
            return json.dumps({"error": "channel is required"})
        if not os.environ.get("SLACK_BOT_TOKEN"):
            return json.dumps({"error": "SLACK_BOT_TOKEN env var is required"})

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{SLACK_API}/conversations.history",
                    params={"channel": channel, "limit": limit},
                    headers=_slack_headers(),
                )
                resp.raise_for_status()
                data = resp.json()

                if not data.get("ok"):
                    return json.dumps({"error": data.get("error", "Unknown Slack error")})

                messages = []
                for msg in data.get("messages", [])[:limit]:
                    messages.append(
                        {
                            "user": msg.get("user"),
                            "text": msg.get("text"),
                            "ts": msg.get("ts"),
                            "type": msg.get("type"),
                            "thread_ts": msg.get("thread_ts"),
                        }
                    )
                return json.dumps({"messages": messages, "count": len(messages), "channel": channel})
        except Exception as e:
            logger.warning("slack_read_messages_error", error=str(e))
            return json.dumps({"error": str(e)})
