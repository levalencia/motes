"""Google service tools — Gmail and Calendar, using saved OAuth tokens."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import httpx


class GmailReadTool:
    """Read recent emails from Gmail."""

    name = "gmail_read"
    description = (
        "Read recent emails from Gmail. "
        "Can filter by query (e.g. 'from:boss@company.com', 'is:unread', 'subject:invoice'). "
        "Returns subject, from, date, and snippet for each email."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Gmail search query (e.g. 'is:unread', 'from:john@example.com')",
            },
            "max_results": {
                "type": "integer",
                "description": "Max emails to return (default 5, max 20)",
            },
        },
        "required": [],
    }

    def __init__(self, access_token: str) -> None:
        self._token = access_token

    async def execute(self, arguments: dict[str, Any]) -> str:
        query = arguments.get("query", "")
        max_results = min(arguments.get("max_results", 5), 20)

        headers = {"Authorization": f"Bearer {self._token}"}
        params: dict[str, Any] = {"maxResults": max_results}
        if query:
            params["q"] = query

        async with httpx.AsyncClient(timeout=15.0) as client:
            # List messages
            resp = await client.get(
                "https://www.googleapis.com/gmail/v1/users/me/messages",
                headers=headers,
                params=params,
            )
            if resp.status_code != 200:
                return json.dumps({"error": f"Gmail API error: {resp.text[:200]}"})

            messages = resp.json().get("messages", [])
            if not messages:
                return json.dumps({"emails": [], "count": 0})

            # Fetch each message's metadata
            emails = []
            for msg in messages[:max_results]:
                detail = await client.get(
                    f"https://www.googleapis.com/gmail/v1/users/me/messages/{msg['id']}",
                    headers=headers,
                    params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]},
                )
                if detail.status_code == 200:
                    data = detail.json()
                    header_map = {}
                    for h in data.get("payload", {}).get("headers", []):
                        header_map[h["name"]] = h["value"]
                    emails.append(
                        {
                            "id": msg["id"],
                            "from": header_map.get("From", ""),
                            "subject": header_map.get("Subject", ""),
                            "date": header_map.get("Date", ""),
                            "snippet": data.get("snippet", ""),
                        }
                    )

            return json.dumps({"emails": emails, "count": len(emails)})


class GmailSendTool:
    """Send an email via Gmail."""

    name = "gmail_send"
    description = (
        "Send an email via Gmail. Provide to, subject, and body. The email is sent from the connected Gmail account."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Recipient email address"},
            "subject": {"type": "string", "description": "Email subject"},
            "body": {"type": "string", "description": "Email body (plain text)"},
        },
        "required": ["to", "subject", "body"],
    }

    def __init__(self, access_token: str) -> None:
        self._token = access_token

    async def execute(self, arguments: dict[str, Any]) -> str:
        import base64

        to = arguments.get("to", "")
        subject = arguments.get("subject", "")
        body = arguments.get("body", "")

        raw_message = f"To: {to}\r\nSubject: {subject}\r\n\r\n{body}"
        encoded = base64.urlsafe_b64encode(raw_message.encode()).decode()

        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://www.googleapis.com/gmail/v1/users/me/messages/send",
                headers=headers,
                json={"raw": encoded},
            )
            if resp.status_code == 200:
                data = resp.json()
                return json.dumps({"status": "sent", "message_id": data.get("id", "")})
            return json.dumps({"error": f"Send failed: {resp.text[:200]}"})


class CalendarListTool:
    """List upcoming events from Google Calendar."""

    name = "calendar_list"
    description = "List upcoming events from Google Calendar. Returns event title, start time, end time, and location."
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "max_results": {
                "type": "integer",
                "description": "Max events to return (default 10)",
            },
            "query": {
                "type": "string",
                "description": "Search text to filter events",
            },
        },
        "required": [],
    }

    def __init__(self, access_token: str) -> None:
        self._token = access_token

    async def execute(self, arguments: dict[str, Any]) -> str:
        max_results = min(arguments.get("max_results", 10), 50)
        query = arguments.get("query", "")

        headers = {"Authorization": f"Bearer {self._token}"}
        now = datetime.now(UTC).isoformat()
        params: dict[str, Any] = {
            "maxResults": max_results,
            "timeMin": now,
            "singleEvents": "true",
            "orderBy": "startTime",
        }
        if query:
            params["q"] = query

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                headers=headers,
                params=params,
            )
            if resp.status_code != 200:
                return json.dumps({"error": f"Calendar API error: {resp.text[:200]}"})

            items = resp.json().get("items", [])
            events = []
            for item in items:
                start = item.get("start", {})
                end = item.get("end", {})
                events.append(
                    {
                        "title": item.get("summary", "(No title)"),
                        "start": start.get("dateTime", start.get("date", "")),
                        "end": end.get("dateTime", end.get("date", "")),
                        "location": item.get("location", ""),
                        "description": (item.get("description", "") or "")[:200],
                    }
                )

            return json.dumps({"events": events, "count": len(events)})


class CalendarCreateTool:
    """Create a new event on Google Calendar."""

    name = "calendar_create"
    description = (
        "Create a new event on Google Calendar. "
        "Provide title, start_time, end_time (ISO format), and optional location."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Event title"},
            "start_time": {
                "type": "string",
                "description": "Start time in ISO format (e.g. 2026-10-01T09:00:00+02:00)",
            },
            "end_time": {
                "type": "string",
                "description": "End time in ISO format",
            },
            "location": {"type": "string", "description": "Event location (optional)"},
            "description": {"type": "string", "description": "Event description (optional)"},
        },
        "required": ["title", "start_time", "end_time"],
    }

    def __init__(self, access_token: str) -> None:
        self._token = access_token

    async def execute(self, arguments: dict[str, Any]) -> str:
        event = {
            "summary": arguments.get("title", ""),
            "start": {"dateTime": arguments.get("start_time", "")},
            "end": {"dateTime": arguments.get("end_time", "")},
        }
        if arguments.get("location"):
            event["location"] = arguments["location"]
        if arguments.get("description"):
            event["description"] = arguments["description"]

        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                headers=headers,
                json=event,
            )
            if resp.status_code == 200:
                data = resp.json()
                return json.dumps(
                    {
                        "status": "created",
                        "event_id": data.get("id", ""),
                        "link": data.get("htmlLink", ""),
                    }
                )
            return json.dumps({"error": f"Create failed: {resp.text[:200]}"})
