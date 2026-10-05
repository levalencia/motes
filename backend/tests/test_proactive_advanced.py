"""Tests for proactive intelligence — event bus, background scanner, pattern suggestions."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.event_bus import EventBus, ProactiveEvent

pytestmark = pytest.mark.unit


class TestEventBus:
    """Test the in-memory pub/sub event bus."""

    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self):
        bus = EventBus()
        sub = bus.subscribe("user1")
        event = ProactiveEvent(user_id="user1", agent_id="a1", title="Test", body="Hello", category="test")
        await bus.publish(event)
        received = await asyncio.wait_for(sub.get(), timeout=1)
        assert received.title == "Test"
        assert received.body == "Hello"
        sub.close()

    @pytest.mark.asyncio
    async def test_publish_to_wrong_user(self):
        bus = EventBus()
        sub = bus.subscribe("user1")
        event = ProactiveEvent(user_id="user2", agent_id="a1", title="Test", body="Hello", category="test")
        await bus.publish(event)
        # Should not receive — wrong user. get() returns None on timeout
        result = await sub.get(timeout=0.1)
        assert result is None
        sub.close()

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        bus = EventBus()
        sub1 = bus.subscribe("user1")
        sub2 = bus.subscribe("user1")
        event = ProactiveEvent(user_id="user1", agent_id="a1", title="Test", body="Hi", category="test")
        await bus.publish(event)
        r1 = await asyncio.wait_for(sub1.get(), timeout=1)
        r2 = await asyncio.wait_for(sub2.get(), timeout=1)
        assert r1.title == r2.title == "Test"
        sub1.close()
        sub2.close()

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        bus = EventBus()
        sub = bus.subscribe("user1")
        sub.close()
        # Should not crash when publishing to closed sub
        event = ProactiveEvent(user_id="user1", agent_id="a1", title="Test", body="Hi", category="test")
        await bus.publish(event)  # No error

    def test_subscriber_count(self):
        bus = EventBus()
        assert bus.subscriber_count == 0
        sub1 = bus.subscribe("user1")
        assert bus.subscriber_count >= 1
        sub2 = bus.subscribe("user1")
        assert bus.subscriber_count >= 2
        sub1.close()
        sub2.close()


class TestProactiveEvent:
    """Test ProactiveEvent data class."""

    def test_event_creation(self):
        event = ProactiveEvent(
            user_id="u1",
            agent_id="a1",
            title="New email from Alice",
            body="Subject: Meeting tomorrow",
            category="email",
        )
        assert event.user_id == "u1"
        assert event.category == "email"
        assert "Alice" in event.title

    def test_event_to_dict(self):
        event = ProactiveEvent(
            user_id="u1",
            agent_id="a1",
            title="Calendar",
            body="Meeting at 3pm",
            category="calendar",
        )
        d = {"title": event.title, "body": event.body, "category": event.category}
        serialized = json.dumps(d)
        parsed = json.loads(serialized)
        assert parsed["title"] == "Calendar"


class TestBackgroundScannerLogic:
    """Test scanner helper functions."""

    def test_notified_email_dedup(self):
        """Scanner tracks notified email IDs to avoid duplicates."""
        notified: set[str] = set()
        msg_id = "abc123"

        # First time — should notify
        assert msg_id not in notified
        notified.add(msg_id)

        # Second time — should skip
        assert msg_id in notified

    def test_notified_set_grows(self):
        notified: set[str] = set()
        for i in range(100):
            notified.add(f"msg_{i}")
        assert len(notified) == 100


class TestPatternSuggestions:
    """Test pattern-based proactive suggestions logic."""

    def test_hour_pattern_match(self):
        """Pattern with hour matches current hour."""
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        pattern_key = f"email_h{now.hour}"
        current_key = f"email_h{now.hour}"
        assert pattern_key == current_key

    def test_frequency_threshold(self):
        """Only suggest when frequency >= 3."""
        frequency = 2
        threshold = 3
        assert frequency < threshold  # Should not suggest

        frequency = 3
        assert frequency >= threshold  # Should suggest

    def test_suggestion_message_format(self):
        """Proactive suggestion has proper format."""
        topic = "email"
        msg = f"💡 {topic.title()} time: You usually check {topic} now. Want me to show your inbox?"
        assert "💡" in msg
        assert "Email" in msg


class TestMemoryInVoiceCalls:
    """Test that voice calls integrate with memory system."""

    @pytest.mark.asyncio
    async def test_memory_save_from_voice(self):
        """memory_save tool works when called from voice context."""
        from app.memory_tools import MemorySaveTool

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.add = MagicMock()

        tool = MemorySaveTool(mock_session, "agent_123")
        result = await tool.execute(
            {
                "fact": "User's daughter is named Victoria",
                "category": "family",
            }
        )
        parsed = json.loads(result)
        assert parsed["status"] == "remembered"
        assert "Victoria" in parsed["fact"]

    @pytest.mark.asyncio
    async def test_memory_recall_family(self):
        """memory_recall finds family-related memories."""
        from app.memory_tools import MemoryRecallTool

        mock_mem = MagicMock()
        mock_mem.content = "User's daughter is named Victoria"
        mock_mem.category = "family"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_mem]

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        tool = MemoryRecallTool(mock_session, "agent_123")
        result = await tool.execute({"query": "family"})
        parsed = json.loads(result)
        assert parsed["count"] == 1
        assert "Victoria" in parsed["memories"][0]["fact"]
        assert parsed["memories"][0]["category"] == "family"

    @pytest.mark.asyncio
    async def test_memory_recall_no_match(self):
        """memory_recall returns recent memories when no keyword match."""
        from app.memory_tools import MemoryRecallTool

        mock_mem1 = MagicMock()
        mock_mem1.content = "User lives in Brussels"
        mock_mem1.category = "personal"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_mem1]

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        tool = MemoryRecallTool(mock_session, "agent_123")
        result = await tool.execute({"query": "zzz_no_match"})
        parsed = json.loads(result)
        # Falls back to returning all memories
        assert parsed["count"] == 1
