"""Messaging tools — send messages via Telegram Bot API.

Uses TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID env vars.
"""

from __future__ import annotations

import json
import os

import httpx
import structlog

from app.tools import Tool

logger = structlog.get_logger()

TELEGRAM_API = "https://api.telegram.org"


class TelegramSendTool(Tool):
    """Send a message via Telegram Bot API."""

    name = "telegram_send"
    description = (
        "Send a message via Telegram. "
        "Can send to the default chat or a specified chat ID. "
        "Supports plain text and Markdown formatting. "
        "Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID env vars."
    )
    parameters = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Message text to send",
            },
            "chat_id": {
                "type": "string",
                "description": "Telegram chat ID (optional, uses TELEGRAM_CHAT_ID env var if not provided)",
            },
            "parse_mode": {
                "type": "string",
                "enum": ["Markdown", "MarkdownV2", "HTML"],
                "description": "Message formatting mode (optional, default: Markdown)",
            },
            "disable_notification": {
                "type": "boolean",
                "description": "Send message silently (default: false)",
            },
        },
        "required": ["text"],
    }

    async def execute(self, arguments: dict) -> str:
        text = arguments.get("text", "")
        chat_id = arguments.get("chat_id") or os.environ.get("TELEGRAM_CHAT_ID", "")
        parse_mode = arguments.get("parse_mode", "Markdown")
        disable_notification = arguments.get("disable_notification", False)

        if not text:
            return json.dumps({"error": "text is required"})
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if not bot_token:
            return json.dumps({"error": "TELEGRAM_BOT_TOKEN env var is required"})
        if not chat_id:
            return json.dumps({"error": "chat_id is required or set TELEGRAM_CHAT_ID env var"})

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{TELEGRAM_API}/bot{bot_token}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": text,
                        "parse_mode": parse_mode,
                        "disable_notification": disable_notification,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                if not data.get("ok"):
                    return json.dumps({"error": data.get("description", "Telegram API error")})

                result = data.get("result", {})
                return json.dumps({
                    "sent": True,
                    "message_id": result.get("message_id"),
                    "chat_id": str(chat_id),
                    "date": result.get("date"),
                })
        except Exception as e:
            logger.warning("telegram_send_error", error=str(e))
            return json.dumps({"error": str(e)})
