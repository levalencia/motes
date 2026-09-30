"""Approval routes: policies, pending requests, approve/deny."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.approvals import (
    ActionRisk,
    list_pending_approvals,
    resolve_approval,
    set_policy,
)
from app.dependencies import get_current_user, get_session
from app.models import Agent, User

router = APIRouter(prefix="/api", tags=["approvals"])


class PolicyCreate(BaseModel):
    tool_name: str
    risk_level: ActionRisk


class PolicyResponse(BaseModel):
    tool_name: str
    risk_level: str


class ApprovalResponse(BaseModel):
    id: str
    agent_id: str
    tool_name: str
    arguments_json: str
    status: str


class ResolveRequest(BaseModel):
    approved: bool
    reason: str | None = None


async def _verify_agent(
    session: AsyncSession, agent_id: str, user_id: str
) -> Agent:
    result = await session.execute(
        select(Agent).where(Agent.id == agent_id, Agent.user_id == user_id)
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post(
    "/agents/{agent_id}/policies",
    response_model=PolicyResponse,
    status_code=201,
)
async def create_policy(
    agent_id: str,
    body: PolicyCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Set an approval policy for a tool on an agent."""
    await _verify_agent(session, agent_id, user.id)
    policy = await set_policy(session, agent_id, body.tool_name, body.risk_level)
    return PolicyResponse(
        tool_name=policy.tool_name, risk_level=policy.risk_level
    )


@router.get(
    "/agents/{agent_id}/approvals",
    response_model=list[ApprovalResponse],
)
async def get_pending(
    agent_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """List pending approval requests for an agent."""
    await _verify_agent(session, agent_id, user.id)
    pending = await list_pending_approvals(session, agent_id)
    return [
        ApprovalResponse(
            id=r.id,
            agent_id=r.agent_id,
            tool_name=r.tool_name,
            arguments_json=r.arguments_json,
            status=r.status,
        )
        for r in pending
    ]


@router.post(
    "/approvals/{request_id}/resolve",
    response_model=ApprovalResponse,
)
async def resolve(
    request_id: str,
    body: ResolveRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Approve or deny a pending approval request."""
    result = await resolve_approval(
        session, request_id, body.approved, body.reason
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Pending request not found")
    return ApprovalResponse(
        id=result.id,
        agent_id=result.agent_id,
        tool_name=result.tool_name,
        arguments_json=result.arguments_json,
        status=result.status,
    )
