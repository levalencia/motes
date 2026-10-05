"""Tests for proactive intelligence — pattern learning and notifications."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.proactive import (
    create_notification,
    extract_people,
    extract_topics,
    get_notifications,
    get_top_patterns,
    get_unread_count,
    learn_from_message,
    mark_read,
)

pytestmark = pytest.mark.unit


@pytest.fixture
async def user_and_agent(async_session: AsyncSession):
    from app.models import Agent, Provider, User

    user = User(username="test", password_hash="x")
    async_session.add(user)
    await async_session.flush()
    provider = Provider(
        user_id=user.id,
        name="test",
        base_url="http://x",
        api_key_encrypted="x",
        model="m",
        is_verified=True,
    )
    async_session.add(provider)
    await async_session.flush()
    agent = Agent(user_id=user.id, provider_id=provider.id, name="a", system_prompt="p")
    async_session.add(agent)
    await async_session.flush()
    return user, agent


class TestTopicExtraction:
    def test_extract_email_topic(self):
        assert "email" in extract_topics("Show me my unread emails")

    def test_extract_calendar_topic(self):
        assert "calendar" in extract_topics("What meetings do I have?")

    def test_extract_weather_topic(self):
        assert "weather" in extract_topics("What's the weather like?")

    def test_extract_search_topic(self):
        assert "search" in extract_topics("Search for AI news")

    def test_extract_multiple_topics(self):
        topics = extract_topics("Search my emails about the meeting")
        assert "email" in topics
        assert "search" in topics

    def test_no_topics(self):
        assert extract_topics("hello there") == []


class TestPeopleExtraction:
    def test_extract_from_pattern(self):
        people = extract_people("send email to Diana about the report")
        assert len(people) > 0

    def test_no_people(self):
        assert extract_people("what time is it") == []


class TestPatternLearning:
    @pytest.mark.asyncio
    async def test_learn_creates_patterns(self, async_session, user_and_agent):
        user, agent = user_and_agent
        await learn_from_message(async_session, user.id, agent.id, "Show me my emails")
        patterns = await get_top_patterns(async_session, user.id)
        assert len(patterns) > 0
        assert any(p.pattern_type == "topic_interest" for p in patterns)

    @pytest.mark.asyncio
    async def test_frequency_increments(self, async_session, user_and_agent):
        user, agent = user_and_agent
        await learn_from_message(async_session, user.id, agent.id, "emails")
        await learn_from_message(async_session, user.id, agent.id, "emails")
        patterns = await get_top_patterns(async_session, user.id)
        email_pattern = next((p for p in patterns if p.pattern_key == "email"), None)
        assert email_pattern is not None
        assert email_pattern.frequency >= 2


class TestNotifications:
    @pytest.mark.asyncio
    async def test_create_notification(self, async_session, user_and_agent):
        user, agent = user_and_agent
        notif = await create_notification(
            async_session,
            user.id,
            agent.id,
            title="Test",
            body="Hello",
            category="info",
        )
        assert notif.id
        assert notif.title == "Test"
        assert not notif.is_read

    @pytest.mark.asyncio
    async def test_unread_count(self, async_session, user_and_agent):
        user, agent = user_and_agent
        await create_notification(async_session, user.id, agent.id, "A", "a")
        await create_notification(async_session, user.id, agent.id, "B", "b")
        count = await get_unread_count(async_session, user.id)
        assert count == 2

    @pytest.mark.asyncio
    async def test_mark_read(self, async_session, user_and_agent):
        user, agent = user_and_agent
        notif = await create_notification(async_session, user.id, agent.id, "X", "x")
        await mark_read(async_session, notif.id)
        count = await get_unread_count(async_session, user.id)
        assert count == 0

    @pytest.mark.asyncio
    async def test_list_notifications(self, async_session, user_and_agent):
        user, agent = user_and_agent
        await create_notification(async_session, user.id, agent.id, "A", "a")
        await create_notification(async_session, user.id, agent.id, "B", "b")
        notifs = await get_notifications(async_session, user.id)
        assert len(notifs) == 2
