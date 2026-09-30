"""Tests for the approval system."""

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


@pytest.mark.unit
class TestActionClassification:
    """Action risk classification tests."""

    @pytest.mark.asyncio
    async def test_builtin_safe_tool(self, session: AsyncSession) -> None:
        risk = await classify_action(session, "agent-1", "current_time")
        assert risk == ActionRisk.SAFE

    @pytest.mark.asyncio
    async def test_unknown_tool_needs_approval(self, session: AsyncSession) -> None:
        risk = await classify_action(session, "agent-1", "send_email")
        assert risk == ActionRisk.NEEDS_APPROVAL

    @pytest.mark.asyncio
    async def test_custom_policy_overrides_default(self, session: AsyncSession) -> None:
        await set_policy(session, "agent-1", "send_email", ActionRisk.SAFE)
        risk = await classify_action(session, "agent-1", "send_email")
        assert risk == ActionRisk.SAFE

    @pytest.mark.asyncio
    async def test_forbidden_policy(self, session: AsyncSession) -> None:
        await set_policy(session, "agent-1", "delete_all", ActionRisk.FORBIDDEN)
        risk = await classify_action(session, "agent-1", "delete_all")
        assert risk == ActionRisk.FORBIDDEN


@pytest.mark.unit
class TestApprovalRequests:
    """Approval request lifecycle tests."""

    @pytest.mark.asyncio
    async def test_create_pending_request(self, session: AsyncSession) -> None:
        req = await create_approval_request(
            session, "agent-1", "send_email", '{"to": "user@example.com"}'
        )
        assert req.status == ApprovalStatus.PENDING
        assert req.tool_name == "send_email"

    @pytest.mark.asyncio
    async def test_approve_request(self, session: AsyncSession) -> None:
        req = await create_approval_request(
            session, "agent-1", "send_email", '{}'
        )
        resolved = await resolve_approval(session, req.id, approved=True)
        assert resolved is not None
        assert resolved.status == ApprovalStatus.APPROVED

    @pytest.mark.asyncio
    async def test_deny_request(self, session: AsyncSession) -> None:
        req = await create_approval_request(
            session, "agent-1", "send_email", '{}'
        )
        resolved = await resolve_approval(
            session, req.id, approved=False, reason="Too risky"
        )
        assert resolved is not None
        assert resolved.status == ApprovalStatus.DENIED
        assert resolved.reason == "Too risky"

    @pytest.mark.asyncio
    async def test_resolve_nonexistent_returns_none(self, session: AsyncSession) -> None:
        resolved = await resolve_approval(session, "fake-id", approved=True)
        assert resolved is None

    @pytest.mark.asyncio
    async def test_double_resolve_returns_none(self, session: AsyncSession) -> None:
        req = await create_approval_request(
            session, "agent-1", "send_email", '{}'
        )
        await resolve_approval(session, req.id, approved=True)
        # Second resolve should fail — already resolved
        second = await resolve_approval(session, req.id, approved=False)
        assert second is None

    @pytest.mark.asyncio
    async def test_list_pending(self, session: AsyncSession) -> None:
        await create_approval_request(session, "agent-1", "tool_a", '{}')
        await create_approval_request(session, "agent-1", "tool_b", '{}')
        req3 = await create_approval_request(session, "agent-1", "tool_c", '{}')
        # Approve one
        await resolve_approval(session, req3.id, approved=True)
        pending = await list_pending_approvals(session, "agent-1")
        assert len(pending) == 2
        names = {r.tool_name for r in pending}
        assert names == {"tool_a", "tool_b"}
