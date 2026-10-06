"""Approval system: action classification and human-in-the-loop gating."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class ActionRisk(StrEnum):
    """Risk classification for agent actions."""

    SAFE = "safe"  # Execute immediately, no approval needed
    NEEDS_APPROVAL = "needs_approval"  # Pause and ask the user
    FORBIDDEN = "forbidden"  # Never execute


class ApprovalStatus(StrEnum):
    """Status of an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


class ApprovalPolicy(Base):
    """Per-agent action classification rules."""

    __tablename__ = "approval_policies"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), index=True)
    tool_name: Mapped[str] = mapped_column(index=True)
    risk_level: Mapped[str] = mapped_column(default=ActionRisk.NEEDS_APPROVAL)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ApprovalRequest(Base):
    """A pending approval request for a specific action."""

    __tablename__ = "approval_requests"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), index=True)
    tool_name: Mapped[str]
    arguments_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(default=ApprovalStatus.PENDING, index=True)
    reason: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


# Default risk classification for built-in tools
DEFAULT_RISK_MAP: dict[str, ActionRisk] = {
    # Safe: read-only, no side effects
    "current_time": ActionRisk.SAFE,
    "calculator": ActionRisk.SAFE,
    "weather": ActionRisk.SAFE,
    "web_search": ActionRisk.SAFE,
    "news": ActionRisk.SAFE,
    "maps": ActionRisk.SAFE,
    "file_list": ActionRisk.SAFE,
    "file_read": ActionRisk.SAFE,
    "file_search": ActionRisk.SAFE,
    "memory_recall": ActionRisk.SAFE,
    "memory_save": ActionRisk.SAFE,
    "gmail_read": ActionRisk.SAFE,
    "calendar_list": ActionRisk.SAFE,
    "outlook_read_email": ActionRisk.SAFE,
    "outlook_calendar": ActionRisk.SAFE,
    "notes_list": ActionRisk.SAFE,
    "notes_read": ActionRisk.SAFE,
    "reminders_list": ActionRisk.SAFE,
    # MCP read-only tools are safe
    "mcp_filesystem__read_file": ActionRisk.SAFE,
    "mcp_filesystem__read_text_file": ActionRisk.SAFE,
    "mcp_filesystem__read_multiple_files": ActionRisk.SAFE,
    "mcp_filesystem__list_directory": ActionRisk.SAFE,
    "mcp_filesystem__list_directory_with_sizes": ActionRisk.SAFE,
    "mcp_filesystem__directory_tree": ActionRisk.SAFE,
    "mcp_filesystem__search_files": ActionRisk.SAFE,
    "mcp_filesystem__get_file_info": ActionRisk.SAFE,
    "mcp_filesystem__list_allowed_directories": ActionRisk.SAFE,
    # MCP write tools need approval (default NEEDS_APPROVAL covers these too)
    "gmail_send": ActionRisk.NEEDS_APPROVAL,
    "outlook_send_email": ActionRisk.NEEDS_APPROVAL,
    "calendar_create": ActionRisk.NEEDS_APPROVAL,
    "reminders_create": ActionRisk.NEEDS_APPROVAL,
    "file_download_url": ActionRisk.NEEDS_APPROVAL,
    "pptx_add_slide": ActionRisk.NEEDS_APPROVAL,
    # MCP tools default to NEEDS_APPROVAL unless overridden
}


async def classify_action(
    session: AsyncSession,
    agent_id: str,
    tool_name: str,
) -> ActionRisk:
    """Classify the risk of an action for a given agent.

    Checks agent-specific policies first, then falls back to defaults.
    """
    result = await session.execute(
        select(ApprovalPolicy).where(
            ApprovalPolicy.agent_id == agent_id,
            ApprovalPolicy.tool_name == tool_name,
        )
    )
    policy = result.scalar_one_or_none()
    if policy is not None:
        return ActionRisk(policy.risk_level)

    return DEFAULT_RISK_MAP.get(tool_name, ActionRisk.NEEDS_APPROVAL)


async def create_approval_request(
    session: AsyncSession,
    agent_id: str,
    tool_name: str,
    arguments_json: str,
) -> ApprovalRequest:
    """Create a pending approval request."""
    request = ApprovalRequest(
        agent_id=agent_id,
        tool_name=tool_name,
        arguments_json=arguments_json,
    )
    session.add(request)
    await session.commit()
    await session.refresh(request)
    return request


async def resolve_approval(
    session: AsyncSession,
    request_id: str,
    approved: bool,
    reason: str | None = None,
) -> ApprovalRequest | None:
    """Approve or deny a pending request."""
    result = await session.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.id == request_id,
            ApprovalRequest.status == ApprovalStatus.PENDING,
        )
    )
    request = result.scalar_one_or_none()
    if request is None:
        return None

    request.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.DENIED
    request.reason = reason
    request.resolved_at = func.now()
    await session.commit()
    await session.refresh(request)
    return request


async def list_pending_approvals(
    session: AsyncSession,
    agent_id: str,
) -> list[ApprovalRequest]:
    """List all pending approval requests for an agent."""
    result = await session.execute(
        select(ApprovalRequest)
        .where(
            ApprovalRequest.agent_id == agent_id,
            ApprovalRequest.status == ApprovalStatus.PENDING,
        )
        .order_by(ApprovalRequest.created_at)
    )
    return list(result.scalars().all())


async def set_policy(
    session: AsyncSession,
    agent_id: str,
    tool_name: str,
    risk_level: ActionRisk,
) -> ApprovalPolicy:
    """Set or update the approval policy for a tool on an agent."""
    result = await session.execute(
        select(ApprovalPolicy).where(
            ApprovalPolicy.agent_id == agent_id,
            ApprovalPolicy.tool_name == tool_name,
        )
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        policy = ApprovalPolicy(
            agent_id=agent_id,
            tool_name=tool_name,
            risk_level=risk_level,
        )
        session.add(policy)
    else:
        policy.risk_level = risk_level
    await session.commit()
    await session.refresh(policy)
    return policy
