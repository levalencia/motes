"""Background scanner — proactive monitoring of connected services.

Runs periodically to check Gmail for new emails, Calendar for upcoming
events, and generates notifications based on learned patterns.
"""

from __future__ import annotations

import asyncio
from datetime import UTC
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Agent, User
from app.proactive import create_notification, get_top_patterns
from app.token_refresh import get_valid_token

logger = structlog.get_logger()

# Track notified email IDs to avoid duplicates (per-process, cleared on restart)
_notified_email_ids: set[str] = set()


async def _notify(
    session: AsyncSession,
    event_bus: Any,
    user_id: str,
    agent_id: str,
    title: str,
    body: str,
    category: str,
) -> None:
    """Save notification to DB and push to active sessions via event bus."""
    await create_notification(session, user_id, agent_id, title, body, category)
    if event_bus is not None:
        from app.event_bus import ProactiveEvent

        await event_bus.publish(ProactiveEvent(
            user_id=user_id,
            agent_id=agent_id,
            title=title,
            body=body,
            category=category,
        ))

SCAN_INTERVAL_SECONDS = 60  # 1 minute


async def scan_gmail(
    session: AsyncSession, user_id: str, agent_id: str,
    access_token: str, event_bus: Any = None,
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

            # Check each unread for new ones we haven't notified about
            for msg_entry in messages[:3]:
                msg_id = msg_entry["id"]
                if msg_id in _notified_email_ids:
                    continue

                detail_resp = await client.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"format": "metadata", "metadataHeaders": ["From", "Subject"]},
                )
                if detail_resp.status_code != 200:
                    continue

                detail = detail_resp.json()
                hdrs = {
                    h["name"]: h["value"]
                    for h in detail.get("payload", {}).get("headers", [])
                }
                sender = hdrs.get("From", "Unknown")
                subject = hdrs.get("Subject", "No subject")

                _notified_email_ids.add(msg_id)

                await _notify(
                    session, event_bus, user_id, agent_id,
                    title=f"📧 New email from {sender.split('<')[0].strip()}",
                    body=subject,
                    category="email",
                )
                logger.info(
                    "scanner_gmail_notification",
                    user_id=user_id,
                    msg_id=msg_id,
                )
    except Exception:
        logger.warning("scanner_gmail_error", exc_info=True)


async def scan_calendar(
    session: AsyncSession, user_id: str, agent_id: str,
    access_token: str, event_bus: Any = None,
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
                    await _notify(
                        session, event_bus, user_id, agent_id,
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


async def check_patterns(
    session: AsyncSession, user_id: str, agent_id: str,
    event_bus: Any = None,
) -> None:
    """Generate proactive suggestions based on learned user patterns."""
    from datetime import datetime

    now = datetime.now(UTC)
    hour = now.hour

    patterns = await get_top_patterns(session, user_id)

    for pattern in patterns:
        if pattern.pattern_type != "time_action":
            continue
        if pattern.frequency < 3:
            continue  # Only suggest frequent actions

        key_parts = pattern.pattern_key.split("_h")
        if len(key_parts) == 2:
            topic = key_parts[0]
            pattern_hour = int(key_parts[1])
            if pattern_hour == hour:
                suggestions = {
                    "email": "You usually check emails now. Want me to show your inbox?",
                    "calendar": "You often check your calendar now. Show today's events?",
                    "news": "Time for your news catch-up. Want the latest?",
                    "weather": "Time for your weather check!",
                    "search": "You often search around now. Anything to find?",
                }
                if topic in suggestions:
                    await _notify(
                        session, event_bus, user_id, agent_id,
                        title=f"💡 {topic.title()} time",
                        body=suggestions[topic],
                        category="suggestion",
                    )
                    logger.info(
                        "scanner_pattern_suggestion",
                        user_id=user_id,
                        topic=topic,
                        hour=hour,
                    )


async def run_scanner(
    session_factory: async_sessionmaker,
    event_bus: Any = None,
) -> None:
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
                        await scan_gmail(session, user.id, agent.id, gmail_token, event_bus)

                    # Check Calendar
                    cal_token = await get_valid_token(session, user.id, "calendar")
                    if cal_token:
                        await scan_calendar(session, user.id, agent.id, cal_token, event_bus)

                    # Proactive suggestions based on patterns
                    await check_patterns(session, user.id, agent.id, event_bus)

                    logger.debug("scanner_user_complete", user_id=user.id)

        except Exception:
            logger.warning("scanner_cycle_error", exc_info=True)

        await asyncio.sleep(SCAN_INTERVAL_SECONDS)
