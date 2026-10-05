"""Outlook tools — read/send email and manage calendar via Microsoft Graph API.

Uses OUTLOOK_ACCESS_TOKEN env var for authentication.
"""

from __future__ import annotations

import json
import os

import httpx
import structlog

from app.tools import Tool

logger = structlog.get_logger()

GRAPH_API = "https://graph.microsoft.com/v1.0"


def _graph_headers() -> dict[str, str]:
    token = os.environ.get("OUTLOOK_ACCESS_TOKEN", "")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


class OutlookReadEmailTool(Tool):
    """Read recent emails from Outlook/Microsoft 365."""

    name = "outlook_read_email"
    description = (
        "Read recent emails from your Outlook/Microsoft 365 inbox. "
        "Returns subject, sender, preview, and date. "
        "Requires OUTLOOK_ACCESS_TOKEN env var."
    )
    parameters = {
        "type": "object",
        "properties": {
            "folder": {
                "type": "string",
                "description": "Mail folder (default: 'inbox'). Options: inbox, sentitems, drafts",
            },
            "search": {
                "type": "string",
                "description": "Search query to filter emails (optional)",
            },
            "limit": {
                "type": "integer",
                "description": "Max emails to return (default: 10)",
            },
            "unread_only": {
                "type": "boolean",
                "description": "Only return unread emails (default: false)",
            },
        },
        "required": [],
    }

    async def execute(self, arguments: dict) -> str:
        folder = arguments.get("folder", "inbox")
        search = arguments.get("search")
        limit = arguments.get("limit", 10)
        unread_only = arguments.get("unread_only", False)

        if not os.environ.get("OUTLOOK_ACCESS_TOKEN"):
            return json.dumps({"error": "OUTLOOK_ACCESS_TOKEN env var is required"})

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                params = {
                    "$top": limit,
                    "$orderby": "receivedDateTime desc",
                    "$select": "subject,from,receivedDateTime,bodyPreview,isRead,importance",
                }
                if search:
                    params["$search"] = f'"{search}"'
                if unread_only:
                    params["$filter"] = "isRead eq false"

                resp = await client.get(
                    f"{GRAPH_API}/me/mailFolders/{folder}/messages",
                    params=params,
                    headers=_graph_headers(),
                )
                resp.raise_for_status()
                data = resp.json()

                emails = []
                for msg in data.get("value", [])[:limit]:
                    from_addr = msg.get("from", {}).get("emailAddress", {})
                    emails.append(
                        {
                            "subject": msg.get("subject"),
                            "from_name": from_addr.get("name"),
                            "from_email": from_addr.get("address"),
                            "date": msg.get("receivedDateTime"),
                            "preview": msg.get("bodyPreview", "")[:200],
                            "is_read": msg.get("isRead"),
                            "importance": msg.get("importance"),
                            "id": msg.get("id"),
                        }
                    )
                return json.dumps({"emails": emails, "count": len(emails)})
        except Exception as e:
            logger.warning("outlook_read_email_error", error=str(e))
            return json.dumps({"error": str(e)})


class OutlookSendEmailTool(Tool):
    """Send an email via Outlook/Microsoft 365."""

    name = "outlook_send_email"
    description = (
        "Send an email via Outlook/Microsoft 365. "
        "Supports to, cc, subject, and HTML or plain text body. "
        "Requires OUTLOOK_ACCESS_TOKEN env var with Mail.Send scope."
    )
    parameters = {
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": "Recipient email address",
            },
            "subject": {
                "type": "string",
                "description": "Email subject line",
            },
            "body": {
                "type": "string",
                "description": "Email body text",
            },
            "cc": {
                "type": "string",
                "description": "CC recipient email address (optional)",
            },
            "is_html": {
                "type": "boolean",
                "description": "Whether body is HTML (default: false, plain text)",
            },
        },
        "required": ["to", "subject", "body"],
    }

    async def execute(self, arguments: dict) -> str:
        to = arguments.get("to", "")
        subject = arguments.get("subject", "")
        body = arguments.get("body", "")
        cc = arguments.get("cc")
        is_html = arguments.get("is_html", False)

        if not to or not subject or not body:
            return json.dumps({"error": "to, subject, and body are required"})
        if not os.environ.get("OUTLOOK_ACCESS_TOKEN"):
            return json.dumps({"error": "OUTLOOK_ACCESS_TOKEN env var is required"})

        try:
            payload = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": "HTML" if is_html else "Text",
                        "content": body,
                    },
                    "toRecipients": [{"emailAddress": {"address": to}}],
                }
            }
            if cc:
                payload["message"]["ccRecipients"] = [{"emailAddress": {"address": cc}}]

            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{GRAPH_API}/me/sendMail",
                    json=payload,
                    headers=_graph_headers(),
                )
                resp.raise_for_status()
                return json.dumps({"sent": True, "to": to, "subject": subject})
        except Exception as e:
            logger.warning("outlook_send_email_error", error=str(e))
            return json.dumps({"error": str(e)})


class OutlookCalendarTool(Tool):
    """Read and create calendar events via Outlook/Microsoft 365."""

    name = "outlook_calendar"
    description = (
        "List upcoming calendar events or create new events in Outlook/Microsoft 365. "
        "Requires OUTLOOK_ACCESS_TOKEN env var with Calendars.ReadWrite scope."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list", "create"],
                "description": "Action: 'list' upcoming events or 'create' a new event",
            },
            "limit": {
                "type": "integer",
                "description": "Max events to list (default: 10, for 'list' action)",
            },
            "subject": {
                "type": "string",
                "description": "Event subject/title (for 'create' action)",
            },
            "start": {
                "type": "string",
                "description": "Start datetime in ISO format, e.g., '2025-01-15T09:00:00' (for 'create')",
            },
            "end": {
                "type": "string",
                "description": "End datetime in ISO format (for 'create')",
            },
            "location": {
                "type": "string",
                "description": "Event location (optional, for 'create')",
            },
            "body": {
                "type": "string",
                "description": "Event description/body (optional, for 'create')",
            },
        },
        "required": ["action"],
    }

    async def execute(self, arguments: dict) -> str:
        action = arguments.get("action", "list")

        if not os.environ.get("OUTLOOK_ACCESS_TOKEN"):
            return json.dumps({"error": "OUTLOOK_ACCESS_TOKEN env var is required"})

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                if action == "list":
                    limit = arguments.get("limit", 10)
                    resp = await client.get(
                        f"{GRAPH_API}/me/events",
                        params={
                            "$top": limit,
                            "$orderby": "start/dateTime",
                            "$select": "subject,start,end,location,organizer,isAllDay",
                        },
                        headers=_graph_headers(),
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    events = []
                    for event in data.get("value", [])[:limit]:
                        events.append(
                            {
                                "subject": event.get("subject"),
                                "start": event.get("start", {}).get("dateTime"),
                                "end": event.get("end", {}).get("dateTime"),
                                "location": event.get("location", {}).get("displayName"),
                                "is_all_day": event.get("isAllDay"),
                                "organizer": event.get("organizer", {}).get("emailAddress", {}).get("name"),
                            }
                        )
                    return json.dumps({"events": events, "count": len(events)})

                elif action == "create":
                    subject = arguments.get("subject", "")
                    start = arguments.get("start", "")
                    end = arguments.get("end", "")
                    if not subject or not start or not end:
                        return json.dumps({"error": "subject, start, and end are required for create"})

                    payload = {
                        "subject": subject,
                        "start": {"dateTime": start, "timeZone": "UTC"},
                        "end": {"dateTime": end, "timeZone": "UTC"},
                    }
                    if arguments.get("location"):
                        payload["location"] = {"displayName": arguments["location"]}
                    if arguments.get("body"):
                        payload["body"] = {"contentType": "Text", "content": arguments["body"]}

                    resp = await client.post(
                        f"{GRAPH_API}/me/events",
                        json=payload,
                        headers=_graph_headers(),
                    )
                    resp.raise_for_status()
                    event = resp.json()
                    return json.dumps(
                        {
                            "created": True,
                            "subject": event.get("subject"),
                            "start": event.get("start", {}).get("dateTime"),
                            "end": event.get("end", {}).get("dateTime"),
                            "id": event.get("id"),
                        }
                    )
                else:
                    return json.dumps({"error": f"Unknown action: {action}"})
        except Exception as e:
            logger.warning("outlook_calendar_error", error=str(e))
            return json.dumps({"error": str(e)})
