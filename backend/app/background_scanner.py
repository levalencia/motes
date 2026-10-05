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
from sqlalchemy.orm import selectinload

from app.models import Agent, User
from app.proactive import create_notification, get_top_patterns
from app.token_refresh import get_valid_token

logger = structlog.get_logger()

# Track notified email IDs to avoid duplicates (per-process, cleared on restart)
_notified_email_ids: set[str] = set()
_notified_patterns: set[str] = set()  # "user_id:topic:hour" — fires once per hour
_last_agentic_run: dict[str, float] = {}  # user_id → timestamp of last LLM proactive


async def _notify(
    session: AsyncSession,
    event_bus: Any,
    user_id: str,
    agent_id: str,
    title: str,
    body: str,
    category: str,
) -> None:
    """Save notification to DB, push to event bus, and add to thread."""
    await create_notification(session, user_id, agent_id, title, body, category)

    # Save to thread — but deduplicate (don't repeat same notification)
    from app.models import Message
    from app.thread import get_or_create_thread

    try:
        thread = await get_or_create_thread(session, agent_id)
        # Check if same notification already exists in last 10 messages
        from sqlalchemy import select

        recent = await session.execute(
            select(Message)
            .where(
                Message.conversation_id == thread.id,
                Message.message_type == "proactive",
            )
            .order_by(Message.created_at.desc())
            .limit(10)
        )
        recent_msgs = recent.scalars().all()
        if any(title in m.content for m in recent_msgs):
            return  # Already notified about this

        session.add(
            Message(
                conversation_id=thread.id,
                role="assistant",
                content=f"💡 **{title}**\n{body}",
                message_type="proactive",
            )
        )
        await session.commit()
    except Exception:
        pass  # Don't break notifications if thread fails

    if event_bus is not None:
        from app.event_bus import ProactiveEvent

        await event_bus.publish(
            ProactiveEvent(
                user_id=user_id,
                agent_id=agent_id,
                title=title,
                body=body,
                category=category,
            )
        )


SCAN_INTERVAL_SECONDS = 60  # 1 minute


async def scan_gmail(
    session: AsyncSession,
    user_id: str,
    agent_id: str,
    access_token: str,
    event_bus: Any = None,
) -> None:
    """Check for new unread emails and create ONE summary notification."""
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

            # Collect new emails we haven't notified about
            new_emails: list[dict[str, str]] = []
            for msg_entry in messages[:5]:
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
                hdrs = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}
                sender = hdrs.get("From", "Unknown").split("<")[0].strip()
                subject = hdrs.get("Subject", "No subject")
                _notified_email_ids.add(msg_id)
                new_emails.append({"sender": sender, "subject": subject})

            # Send ONE summary for all new emails
            if new_emails:
                if len(new_emails) == 1:
                    title = f"📧 New email from {new_emails[0]['sender']}"
                    body = new_emails[0]["subject"]
                else:
                    title = f"📧 {len(new_emails)} new emails"
                    body = "\n".join(f"• {e['sender']}: {e['subject']}" for e in new_emails)

                await _notify(
                    session,
                    event_bus,
                    user_id,
                    agent_id,
                    title=title,
                    body=body[:300],
                    category="email",
                )
                logger.info(
                    "scanner_gmail_notification",
                    user_id=user_id,
                    count=len(new_emails),
                )
    except Exception:
        logger.warning("scanner_gmail_error", exc_info=True)


async def scan_calendar(
    session: AsyncSession,
    user_id: str,
    agent_id: str,
    access_token: str,
    event_bus: Any = None,
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
                        session,
                        event_bus,
                        user_id,
                        agent_id,
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
    session: AsyncSession,
    user_id: str,
    agent_id: str,
    event_bus: Any = None,
    interval_minutes: int = 60,
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
            continue  # Only trigger on frequent actions

        key_parts = pattern.pattern_key.split("_h")
        if len(key_parts) == 2:
            topic = key_parts[0]
            pattern_hour = int(key_parts[1])
            if pattern_hour == hour:
                # Dedup: based on user's interval setting
                dedup_key = f"{user_id}:{topic}:{hour}"
                if dedup_key in _notified_patterns:
                    continue
                # Actually execute the tool and deliver results
                result = await _execute_proactive_tool(topic)
                if result:
                    await _notify(
                        session,
                        event_bus,
                        user_id,
                        agent_id,
                        title=result["title"],
                        body=result["body"],
                        category=topic,
                    )
                    _notified_patterns.add(dedup_key)
                    logger.info(
                        "scanner_pattern_executed",
                        user_id=user_id,
                        topic=topic,
                        hour=hour,
                    )


async def _execute_proactive_tool(topic: str) -> dict | None:
    """Execute a tool proactively based on the topic pattern."""
    try:
        if topic == "weather":
            from app.weather_tool import WeatherTool

            tool = WeatherTool()
            result = await tool.execute({"location": "auto"})
            import json

            data = json.loads(result)
            temp = data.get("current_temperature", "?")
            desc = data.get("description", "")
            return {
                "title": f"🌤️ Weather: {temp}°C",
                "body": desc[:200] if desc else f"Current temperature: {temp}°C",
            }

        elif topic == "news":
            from app.news_tool import NewsTool

            tool = NewsTool()
            result = await tool.execute({"query": "top news today"})
            import json

            data = json.loads(result)
            headlines = data.get("articles", data.get("results", []))
            if isinstance(headlines, list) and headlines:
                top3 = headlines[:3]
                body = "\n".join(f"• {h.get('title', h) if isinstance(h, dict) else h}" for h in top3)
                return {"title": "📰 Your daily news", "body": body[:300]}

        elif topic == "email":
            return {
                "title": "📧 Email time",
                "body": "You usually check your email now. Say 'read my email' to catch up.",
            }

        elif topic == "calendar":
            return {
                "title": "📅 Calendar check",
                "body": "You often check your schedule now. Say 'what's on my calendar today?' to see events.",
            }

    except Exception:
        pass
    return None


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
                    # Skip if user disabled proactive
                    if not getattr(user, "proactive_enabled", True):
                        continue

                    # Get user's first agent (for notification scoping)
                    agent_result = await session.execute(
                        select(Agent).where(Agent.user_id == user.id).options(selectinload(Agent.provider)).limit(1)
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

                    # Agentic proactive — LLM decides what to check
                    proactive_on = getattr(user, "proactive_enabled", True)
                    logger.info(
                        "scanner_proactive_check",
                        user_id=user.id,
                        proactive_enabled=proactive_on,
                    )
                    if proactive_on:
                        import time

                        interval = getattr(user, "proactive_interval_minutes", 60)
                        last_run = _last_agentic_run.get(user.id, 0)
                        elapsed = time.time() - last_run
                        needed = interval * 60
                        logger.info(
                            "scanner_proactive_timing",
                            elapsed=int(elapsed),
                            needed=needed,
                            will_run=elapsed >= needed,
                        )
                        if elapsed >= needed:
                            try:
                                from app.agentic_proactive import run_agentic_proactive

                                logger.info("scanner_agentic_starting")
                                result = await run_agentic_proactive(
                                    session,
                                    user,
                                    agent,
                                    agent.provider,
                                    event_bus,
                                )
                                logger.info("scanner_agentic_done", result_len=len(result) if result else 0)
                                _last_agentic_run[user.id] = time.time()
                            except Exception:
                                logger.warning("agentic_proactive_skip", exc_info=True)

                    logger.info("scanner_user_complete", user_id=user.id)

        except Exception:
            logger.warning("scanner_cycle_error", exc_info=True)

        await asyncio.sleep(SCAN_INTERVAL_SECONDS)
