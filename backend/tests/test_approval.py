"""TDD tests for the approval system."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.approvals import (
    ActionRisk,
    ApprovalStatus,
    classify_action,
    create_approval_request,
    list_pending_approvals,
    resolve_approval,
    set_policy,
)
from app.models import Agent, Provider, User

pytestmark = pytest.mark.unit


@pytest.fixture
async def user(session: AsyncSession) -> User:
    """Create a test user."""
    u = User(username="approval_tester", password_hash="hash")
    session.add(u)
    await session.commit()
    await session.refresh(u)
    return u


@pytest.fixture
async def provider(session: AsyncSession, user: User) -> Provider:
    """Create a test provider."""
    p = Provider(
        user_id=user.id,
        name="test-provider",
        base_url="http://localhost",
        api_key_encrypted="enc",
        model="test-model",
    )
    session.add(p)
    await session.commit()
    await session.refresh(p)
    return p


@pytest.fixture
async def agent(session: AsyncSession, user: User, provider: Provider) -> Agent:
    """Create a test agent."""
    a = Agent(
        user_id=user.id,
        provider_id=provider.id,
        name="test-agent",
    )
    session.add(a)
    await session.commit()
    await session.refresh(a)
    return a


async def test_create_approval_request(session: AsyncSession, agent: Agent) -> None:
    """Agent creates a pending approval request."""
    req = await create_approval_request(
        session,
        agent_id=agent.id,
        tool_name="send_email",
        arguments_json='{"to": "user@example.com", "body": "Hello"}',
    )
    assert req.id is not None
    assert req.agent_id == agent.id
    assert req.tool_name == "send_email"
    assert req.status == ApprovalStatus.PENDING
    assert req.resolved_at is None


async def test_approve_request(session: AsyncSession, agent: Agent) -> None:
    """User approves a pending request."""
    req = await create_approval_request(
        session, agent_id=agent.id, tool_name="delete_file",
        arguments_json='{"path": "/tmp/test.txt"}',
    )
    resolved = await resolve_approval(session, req.id, approved=True, reason="Looks good")
    assert resolved is not None
    assert resolved.status == ApprovalStatus.APPROVED
    assert resolved.reason == "Looks good"


async def test_deny_request(session: AsyncSession, agent: Agent) -> None:
    """User denies a pending request."""
    req = await create_approval_request(
        session, agent_id=agent.id, tool_name="create_reminder",
        arguments_json='{"text": "Buy milk"}',
    )
    resolved = await resolve_approval(session, req.id, approved=False, reason="Not needed")
    assert resolved is not None
    assert resolved.status == ApprovalStatus.DENIED
    assert resolved.reason == "Not needed"


async def test_list_pending_approvals(session: AsyncSession, agent: Agent) -> None:
    """API returns only pending items for a given agent."""
    # Create 3 requests; approve one, deny another
    r1 = await create_approval_request(session, agent.id, "send_email", "{}")
    r2 = await create_approval_request(session, agent.id, "delete_file", "{}")
    r3 = await create_approval_request(session, agent.id, "create_reminder", "{}")

    await resolve_approval(session, r1.id, approved=True)
    await resolve_approval(session, r2.id, approved=False)

    pending = await list_pending_approvals(session, agent.id)
    assert len(pending) == 1
    assert pending[0].id == r3.id


async def test_approval_timeout_expired(session: AsyncSession, agent: Agent) -> None:
    """An approval that is resolved as expired is no longer pending."""
    req = await create_approval_request(session, agent.id, "send_email", "{}")

    # Simulate timeout by directly setting status to expired
    from sqlalchemy import select

    from app.approvals import ApprovalRequest

    result = await session.execute(
        select(ApprovalRequest).where(ApprovalRequest.id == req.id)
    )
    ar = result.scalar_one()
    ar.status = ApprovalStatus.EXPIRED
    await session.commit()

    pending = await list_pending_approvals(session, agent.id)
    assert len(pending) == 0


async def test_classify_action_default(session: AsyncSession, agent: Agent) -> None:
    """Unknown tools default to NEEDS_APPROVAL."""
    risk = await classify_action(session, agent.id, "unknown_tool")
    assert risk == ActionRisk.NEEDS_APPROVAL


async def test_classify_action_safe_builtin(session: AsyncSession, agent: Agent) -> None:
    """Built-in safe tools are classified as SAFE."""
    risk = await classify_action(session, agent.id, "current_time")
    assert risk == ActionRisk.SAFE


async def test_classify_action_custom_policy(session: AsyncSession, agent: Agent) -> None:
    """Custom policy overrides default classification."""
    await set_policy(session, agent.id, "send_email", ActionRisk.SAFE)
    risk = await classify_action(session, agent.id, "send_email")
    assert risk == ActionRisk.SAFE


async def test_resolve_nonexistent_request(session: AsyncSession) -> None:
    """Resolving a nonexistent request returns None."""
    result = await resolve_approval(session, "nonexistent-id", approved=True)
    assert result is None


async def test_resolve_already_resolved(session: AsyncSession, agent: Agent) -> None:
    """Cannot resolve an already-resolved request."""
    req = await create_approval_request(session, agent.id, "send_email", "{}")
    await resolve_approval(session, req.id, approved=True)
    # Try to resolve again
    result = await resolve_approval(session, req.id, approved=False)
    assert result is None  # Already resolved, not pending
