"""Background scanner — proactive monitoring of connected services.

Runs periodically to check Gmail for new emails, Calendar for upcoming
events, and generates notifications based on learned patterns.
"""

from __future__ import annotations

import asyncio
from datetime import UTC

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Agent, User
from app.proactive import create_notification
from app.token_refresh import get_valid_token

logger = structlog.get_logger()

SCAN_INTERVAL_SECONDS = 300  # 5 minutes


async def scan_gmail(
    session: AsyncSession, user_id: str, agent_id: str, access_token: str
) -> None:
    """Check for new unread emails and create notifications."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"q": "is:unread", "maxResults": 5},
            )
            if resp.status_code != 200:
                return

            data = resp.json()
            messages = data.get("messages", [])
            if not messages:
                return

            # Get details of first unread
            msg_id = messages[0]["id"]
            detail_resp = await client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"format": "metadata", "metadataHeaders": ["From", "Subject"]},
            )
            if detail_resp.status_code != 200:
                return

            detail = detail_resp.json()
            headers = {
                h["name"]: h["value"]
                for h in detail.get("payload", {}).get("headers", [])
            }
            sender = headers.get("From", "Unknown")
            subject = headers.get("Subject", "No subject")

            await create_notification(
                session, user_id, agent_id,
                title=f"📧 New email from {sender.split('<')[0].strip()}",
                body=subject,
                category="email",
            )
            logger.info(
                "scanner_gmail_notification",
                user_id=user_id,
                unread=len(messages),
            )
    except Exception:
        logger.warning("scanner_gmail_error", exc_info=True)


async def scan_calendar(
    session: AsyncSession, user_id: str, agent_id: str, access_token: str
) -> None:
    """Check for upcoming calendar events and create notifications."""
    from datetime import datetime, timedelta

    import httpx

    try:
        now = datetime.now(UTC)
        time_min = now.isoformat()
        time_max = (now + timedelta(hours=1)).isoformat()

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "timeMin": time_min,
                    "timeMax": time_max,
                    "singleEvents": "true",
                    "orderBy": "startTime",
                    "maxResults": 5,
                },
            )
            if resp.status_code != 200:
                return

            events = resp.json().get("items", [])
            for event in events:
                summary = event.get("summary", "Untitled event")
                start = event.get("start", {}).get("dateTime", "")
                if start:
                    await create_notification(
                        session, user_id, agent_id,
                        title=f"📅 Upcoming: {summary}",
                        body=f"Starting at {start}",
                        category="calendar",
                    )
            if events:
                logger.info(
                    "scanner_calendar_notification",
                    user_id=user_id,
                    events=len(events),
                )
    except Exception:
        logger.warning("scanner_calendar_error", exc_info=True)


async def run_scanner(session_factory: async_sessionmaker) -> None:
    """Main scanner loop — runs forever, scanning every SCAN_INTERVAL_SECONDS."""
    logger.info("scanner_started", interval=SCAN_INTERVAL_SECONDS)

    while True:
        try:
            async with session_factory() as session:
                # Get all users
                result = await session.execute(select(User))
                users = result.scalars().all()

                for user in users:
                    # Get user's first agent (for notification scoping)
                    agent_result = await session.execute(
                        select(Agent).where(Agent.user_id == user.id).limit(1)
                    )
                    agent = agent_result.scalar_one_or_none()
                    if not agent:
                        continue

                    # Check Gmail
                    gmail_token = await get_valid_token(session, user.id, "gmail")
                    if gmail_token:
                        await scan_gmail(session, user.id, agent.id, gmail_token)

                    # Check Calendar
                    cal_token = await get_valid_token(session, user.id, "calendar")
                    if cal_token:
                        await scan_calendar(session, user.id, agent.id, cal_token)

                    logger.debug("scanner_user_complete", user_id=user.id)

        except Exception:
            logger.warning("scanner_cycle_error", exc_info=True)

        await asyncio.sleep(SCAN_INTERVAL_SECONDS)
