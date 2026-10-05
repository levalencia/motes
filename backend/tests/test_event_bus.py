"""Tests for the event bus — pub/sub for proactive notifications."""

import pytest

from app.event_bus import EventBus, ProactiveEvent

pytestmark = pytest.mark.unit


class TestEventBus:
    def test_initial_state(self):
        bus = EventBus()
        assert bus.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self):
        bus = EventBus()
        sub = bus.subscribe("user1")
        assert bus.subscriber_count == 1

        event = ProactiveEvent(
            user_id="user1",
            agent_id="a1",
            title="Test",
            body="Hello",
            category="info",
        )
        count = await bus.publish(event)
        assert count == 1

        received = await sub.get(timeout=1.0)
        assert received is not None
        assert received.title == "Test"
        assert received.body == "Hello"

    @pytest.mark.asyncio
    async def test_no_subscribers(self):
        bus = EventBus()
        event = ProactiveEvent(
            user_id="user1",
            agent_id="a1",
            title="Test",
            body="Hello",
            category="info",
        )
        count = await bus.publish(event)
        assert count == 0

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        bus = EventBus()
        sub1 = bus.subscribe("user1")
        sub2 = bus.subscribe("user1")
        assert bus.subscriber_count == 2

        event = ProactiveEvent(
            user_id="user1",
            agent_id="a1",
            title="Test",
            body="Hello",
            category="info",
        )
        count = await bus.publish(event)
        assert count == 2

        r1 = await sub1.get(timeout=1.0)
        r2 = await sub2.get(timeout=1.0)
        assert r1 is not None
        assert r2 is not None

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        bus = EventBus()
        sub = bus.subscribe("user1")
        assert bus.subscriber_count == 1
        sub.close()
        assert bus.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_timeout_returns_none(self):
        bus = EventBus()
        sub = bus.subscribe("user1")
        result = await sub.get(timeout=0.1)
        assert result is None
        sub.close()

    @pytest.mark.asyncio
    async def test_different_users_isolated(self):
        bus = EventBus()
        sub1 = bus.subscribe("user1")
        sub2 = bus.subscribe("user2")

        event = ProactiveEvent(
            user_id="user1",
            agent_id="a1",
            title="For user1",
            body="x",
            category="info",
        )
        await bus.publish(event)

        r1 = await sub1.get(timeout=0.5)
        r2 = await sub2.get(timeout=0.1)
        assert r1 is not None
        assert r1.title == "For user1"
        assert r2 is None  # user2 didn't get it

        sub1.close()
        sub2.close()
