"""Proactive intelligence — learn patterns, monitor services, push notifications.

Like OpenAI Dots: the agent doesn't wait for you to ask. It monitors your
connected services and learns what you need before you need it.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class UserPattern(Base):
    """Learned pattern from user interactions."""

    __tablename__ = "user_patterns"

    id: Mapped[str] = mapped_column(
        primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    agent_id: Mapped[str] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), index=True
    )
    pattern_type: Mapped[str] = mapped_column(index=True)
    # Types: "time_action", "topic_interest", "person_importance", "routine"
    pattern_key: Mapped[str]
    # e.g. "weather_morning", "email_check", "news_ai"
    pattern_data: Mapped[str] = mapped_column(Text, default="{}")
    # JSON with: frequency, times, last_seen, confidence
    frequency: Mapped[int] = mapped_column(default=1)
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Notification(Base):
    """Proactive notification pushed to user."""

    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(
        primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    agent_id: Mapped[str] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str]
    body: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(default="info", index=True)
    # Categories: "email", "calendar", "suggestion", "reminder", "alert"
    is_read: Mapped[bool] = mapped_column(default=False)
    action_url: Mapped[str] = mapped_column(default="")
    # Optional: deep link to chat, email, calendar event
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ── Pattern extraction from messages ─────────────────────────────

TOPIC_KEYWORDS: dict[str, list[str]] = {
    "weather": ["weather", "temperature", "forecast", "rain", "sunny"],
    "email": ["email", "inbox", "unread", "gmail", "send email", "mail"],
    "calendar": ["calendar", "meeting", "schedule", "appointment", "event"],
    "news": ["news", "latest", "headlines", "what happened"],
    "files": ["file", "document", "pptx", "powerpoint", "pdf", "folder"],
    "search": ["search", "google", "look up", "find out", "web search"],
    "time": ["time", "what time", "date", "clock"],
}


def extract_topics(message: str) -> list[str]:
    """Extract topic categories from a user message."""
    lower = message.lower()
    return [
        topic for topic, keywords in TOPIC_KEYWORDS.items()
        if any(kw in lower for kw in keywords)
    ]


def extract_people(message: str) -> list[str]:
    """Extract mentioned people/contacts from a message."""
    people = []
    # Simple extraction: look for "from X", "to X", "email X"
    import re

    patterns = [
        r"(?:from|to|email|send to|forward to|message)\s+(\w+(?:\s+\w+)?)",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, message, re.IGNORECASE)
        people.extend(matches)
    return people


async def learn_from_message(
    session: AsyncSession,
    user_id: str,
    agent_id: str,
    message: str,
) -> None:
    """Extract patterns from a user message and update learned patterns."""
    now = datetime.now(UTC)
    hour = now.hour

    # Extract topics
    topics = extract_topics(message)
    for topic in topics:
        key = f"{topic}_h{hour}"
        await _upsert_pattern(
            session, user_id, agent_id,
            "time_action", key,
            {"topic": topic, "hour": hour},
        )
        await _upsert_pattern(
            session, user_id, agent_id,
            "topic_interest", topic,
            {"topic": topic},
        )

    # Extract people
    people = extract_people(message)
    for person in people:
        await _upsert_pattern(
            session, user_id, agent_id,
            "person_importance", person.lower().strip(),
            {"name": person},
        )

    await session.commit()


async def _upsert_pattern(
    session: AsyncSession,
    user_id: str,
    agent_id: str,
    pattern_type: str,
    pattern_key: str,
    data: dict,
) -> None:
    """Insert or update a pattern, incrementing frequency."""
    result = await session.execute(
        select(UserPattern).where(
            UserPattern.user_id == user_id,
            UserPattern.agent_id == agent_id,
            UserPattern.pattern_type == pattern_type,
            UserPattern.pattern_key == pattern_key,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.frequency += 1
        existing.last_seen = func.now()
        existing.pattern_data = json.dumps(data)
    else:
        pattern = UserPattern(
            user_id=user_id,
            agent_id=agent_id,
            pattern_type=pattern_type,
            pattern_key=pattern_key,
            pattern_data=json.dumps(data),
        )
        session.add(pattern)


async def get_top_patterns(
    session: AsyncSession, user_id: str, limit: int = 20
) -> list[UserPattern]:
    """Get the most frequent patterns for a user."""
    result = await session.execute(
        select(UserPattern)
        .where(UserPattern.user_id == user_id)
        .order_by(UserPattern.frequency.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# ── Notifications ─────────────────────────────────────────────────

async def create_notification(
    session: AsyncSession,
    user_id: str,
    agent_id: str,
    title: str,
    body: str,
    category: str = "info",
    action_url: str = "",
) -> Notification:
    """Create a notification for the user."""
    notif = Notification(
        user_id=user_id,
        agent_id=agent_id,
        title=title,
        body=body,
        category=category,
        action_url=action_url,
    )
    session.add(notif)
    await session.commit()
    await session.refresh(notif)
    return notif


async def get_notifications(
    session: AsyncSession,
    user_id: str,
    unread_only: bool = False,
    limit: int = 50,
) -> list[Notification]:
    """Get notifications for a user."""
    stmt = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    stmt = stmt.order_by(Notification.created_at.desc()).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def mark_read(session: AsyncSession, notification_id: str) -> None:
    """Mark a notification as read."""
    result = await session.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notif = result.scalar_one_or_none()
    if notif:
        notif.is_read = True
        await session.commit()


async def get_unread_count(session: AsyncSession, user_id: str) -> int:
    """Count unread notifications."""
    result = await session.execute(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
    )
    return result.scalar() or 0
