"""Notification routes: list, mark read, unread count, patterns."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_session
from app.models import User
from app.proactive import get_notifications, get_top_patterns, get_unread_count, mark_read

logger = structlog.get_logger()

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotificationResponse(BaseModel):
    id: str
    title: str
    body: str
    category: str
    is_read: bool
    action_url: str


class UnreadCountResponse(BaseModel):
    count: int


class PatternResponse(BaseModel):
    pattern_type: str
    pattern_key: str
    frequency: int


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    unread_only: bool = False,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """List notifications for the current user."""
    notifs = await get_notifications(session, user.id, unread_only)
    return [
        NotificationResponse(
            id=n.id,
            title=n.title,
            body=n.body,
            category=n.category,
            is_read=n.is_read,
            action_url=n.action_url,
        )
        for n in notifs
    ]


@router.get("/unread-count", response_model=UnreadCountResponse)
async def unread_count(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Get count of unread notifications."""
    count = await get_unread_count(session, user.id)
    return UnreadCountResponse(count=count)


@router.post("/{notification_id}/read", status_code=204)
async def read_notification(
    notification_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Mark a notification as read."""
    await mark_read(session, notification_id)


@router.get("/patterns", response_model=list[PatternResponse])
async def list_patterns(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """View learned patterns about the user."""
    patterns = await get_top_patterns(session, user.id)
    return [
        PatternResponse(
            pattern_type=p.pattern_type,
            pattern_key=p.pattern_key,
            frequency=p.frequency,
        )
        for p in patterns
    ]
