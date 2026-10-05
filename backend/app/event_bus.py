"""In-memory event bus for pushing real-time notifications to active sessions.

Pub/sub pattern: scanner publishes events, active chat/call sessions subscribe.
Each user gets their own channel. Multiple subscribers per user are supported
(e.g., one chat tab + one call tab).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import structlog

logger = structlog.get_logger()


@dataclass
class ProactiveEvent:
    """A proactive notification pushed to an active session."""

    user_id: str
    agent_id: str
    title: str
    body: str
    category: str  # "email", "calendar", "suggestion"
    action: str = ""  # Optional: "read_email", "show_calendar"


class EventBus:
    """In-memory pub/sub for real-time proactive notifications.

    Usage:
        bus = EventBus()

        # In chat/call route (subscriber):
        async for event in bus.subscribe(user_id):
            send_to_client(event)

        # In background scanner (publisher):
        await bus.publish(ProactiveEvent(user_id=..., title=..., body=...))
    """

    def __init__(self) -> None:
        self._channels: dict[str, list[asyncio.Queue[ProactiveEvent]]] = {}

    def subscribe(self, user_id: str) -> _Subscription:
        """Subscribe to events for a user. Returns an async iterator."""
        queue: asyncio.Queue[ProactiveEvent] = asyncio.Queue()
        if user_id not in self._channels:
            self._channels[user_id] = []
        self._channels[user_id].append(queue)
        logger.debug("event_bus_subscribe", user_id=user_id)
        return _Subscription(self, user_id, queue)

    async def publish(self, event: ProactiveEvent) -> int:
        """Publish an event to all subscribers for a user.

        Returns the number of subscribers that received it.
        """
        queues = self._channels.get(event.user_id, [])
        for q in queues:
            await q.put(event)
        if queues:
            logger.info(
                "event_bus_published",
                user_id=event.user_id,
                title=event.title,
                subscribers=len(queues),
            )
        return len(queues)

    def _unsubscribe(self, user_id: str, queue: asyncio.Queue) -> None:
        """Remove a subscriber."""
        if user_id in self._channels:
            self._channels[user_id] = [q for q in self._channels[user_id] if q is not queue]
            if not self._channels[user_id]:
                del self._channels[user_id]
        logger.debug("event_bus_unsubscribe", user_id=user_id)

    @property
    def subscriber_count(self) -> int:
        """Total active subscribers across all users."""
        return sum(len(qs) for qs in self._channels.values())


class _Subscription:
    """Async iterator for receiving events from the bus."""

    def __init__(self, bus: EventBus, user_id: str, queue: asyncio.Queue[ProactiveEvent]) -> None:
        self._bus = bus
        self._user_id = user_id
        self._queue = queue

    def __aiter__(self):
        return self

    async def __anext__(self) -> ProactiveEvent:
        return await self._queue.get()

    async def get(self, timeout: float = 1.0) -> ProactiveEvent | None:
        """Get next event with timeout. Returns None on timeout."""
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=timeout)
        except TimeoutError:
            return None

    def close(self) -> None:
        """Unsubscribe from the bus."""
        self._bus._unsubscribe(self._user_id, self._queue)
