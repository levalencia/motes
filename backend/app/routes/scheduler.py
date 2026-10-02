"""Scheduler routes: task CRUD, pause/resume, run history."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_session
from app.models import Agent, User
from app.scheduler import (
    create_task,
    delete_task,
    list_runs,
    list_tasks,
    pause_task,
    resume_task,
)

router = APIRouter(prefix="/api/agents/{agent_id}/tasks", tags=["scheduler"])


class TaskCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    prompt: str = Field(min_length=1)
    cron_expression: str = Field(min_length=1)
    max_runs: int | None = None


class TaskResponse(BaseModel):
    id: str
    agent_id: str
    name: str
    prompt: str
    cron_expression: str
    status: str
    run_count: int
    max_runs: int | None
    enabled: bool = True

    @classmethod
    def from_task(cls, task: Any) -> TaskResponse:
        return cls(
            id=task.id,
            agent_id=task.agent_id,
            name=task.name,
            prompt=task.prompt,
            cron_expression=task.cron_expression,
            status=task.status,
            run_count=task.run_count,
            max_runs=task.max_runs,
            enabled=task.status == "active",
        )


class RunResponse(BaseModel):
    id: str
    task_id: str
    status: str
    result: str | None
    error: str | None


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


@router.post("", response_model=TaskResponse, status_code=201)
async def create_scheduled_task(
    agent_id: str,
    body: TaskCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Create a new scheduled task."""
    await _verify_agent(session, agent_id, user.id)
    task = await create_task(
        session, agent_id, body.name, body.prompt,
        body.cron_expression, body.max_runs,
    )
    return TaskResponse(
        id=task.id, agent_id=task.agent_id, name=task.name,
        prompt=task.prompt, cron_expression=task.cron_expression,
        status=task.status, run_count=task.run_count, max_runs=task.max_runs,
    )


@router.get("", response_model=list[TaskResponse])
async def get_tasks(
    agent_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """List scheduled tasks for an agent."""
    await _verify_agent(session, agent_id, user.id)
    tasks = await list_tasks(session, agent_id)
    return [
        TaskResponse(
            id=t.id, agent_id=t.agent_id, name=t.name,
            prompt=t.prompt, cron_expression=t.cron_expression,
            status=t.status, run_count=t.run_count, max_runs=t.max_runs,
        )
        for t in tasks
    ]


@router.post("/{task_id}/pause", response_model=TaskResponse)
async def pause(
    agent_id: str,
    task_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Pause a scheduled task."""
    await _verify_agent(session, agent_id, user.id)
    task = await pause_task(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(
        id=task.id, agent_id=task.agent_id, name=task.name,
        prompt=task.prompt, cron_expression=task.cron_expression,
        status=task.status, run_count=task.run_count, max_runs=task.max_runs,
    )


@router.post("/{task_id}/resume", response_model=TaskResponse)
async def resume(
    agent_id: str,
    task_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Resume a paused task."""
    await _verify_agent(session, agent_id, user.id)
    task = await resume_task(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(
        id=task.id, agent_id=task.agent_id, name=task.name,
        prompt=task.prompt, cron_expression=task.cron_expression,
        status=task.status, run_count=task.run_count, max_runs=task.max_runs,
    )


@router.delete("/{task_id}", status_code=204)
async def remove_task(
    agent_id: str,
    task_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Delete a scheduled task."""
    await _verify_agent(session, agent_id, user.id)
    deleted = await delete_task(session, task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")


@router.get("/{task_id}/runs", response_model=list[RunResponse])
async def get_runs(
    agent_id: str,
    task_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Get run history for a task."""
    await _verify_agent(session, agent_id, user.id)
    runs = await list_runs(session, task_id)
    return [
        RunResponse(
            id=r.id, task_id=r.task_id, status=r.status,
            result=r.result, error=r.error,
        )
        for r in runs
    ]
