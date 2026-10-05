"""Cron-based task scheduler for autonomous agent work."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class TaskStatus(StrEnum):
    """Scheduled task status."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class RunStatus(StrEnum):
    """Individual task run status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScheduledTask(Base):
    """A recurring or one-shot task assigned to an agent."""

    __tablename__ = "scheduled_tasks"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), index=True)
    name: Mapped[str]
    prompt: Mapped[str] = mapped_column(Text)
    cron_expression: Mapped[str]  # e.g. "0 9 * * *" or "once"
    status: Mapped[str] = mapped_column(default=TaskStatus.ACTIVE, index=True)
    max_runs: Mapped[int | None] = mapped_column(default=None)  # None = unlimited
    run_count: Mapped[int] = mapped_column(default=0)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TaskRun(Base):
    """Record of a single execution of a scheduled task."""

    __tablename__ = "task_runs"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(ForeignKey("scheduled_tasks.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(default=RunStatus.PENDING)
    result: Mapped[str | None] = mapped_column(Text, default=None)
    error: Mapped[str | None] = mapped_column(Text, default=None)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


async def create_task(
    session: AsyncSession,
    agent_id: str,
    name: str,
    prompt: str,
    cron_expression: str,
    max_runs: int | None = None,
) -> ScheduledTask:
    """Create a new scheduled task."""
    task = ScheduledTask(
        agent_id=agent_id,
        name=name,
        prompt=prompt,
        cron_expression=cron_expression,
        max_runs=max_runs,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def list_tasks(session: AsyncSession, agent_id: str) -> list[ScheduledTask]:
    """List all tasks for an agent."""
    result = await session.execute(
        select(ScheduledTask).where(ScheduledTask.agent_id == agent_id).order_by(ScheduledTask.created_at.desc())
    )
    return list(result.scalars().all())


async def pause_task(session: AsyncSession, task_id: str) -> ScheduledTask | None:
    """Pause a task."""
    result = await session.execute(select(ScheduledTask).where(ScheduledTask.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        return None
    task.status = TaskStatus.PAUSED
    await session.commit()
    await session.refresh(task)
    return task


async def resume_task(session: AsyncSession, task_id: str) -> ScheduledTask | None:
    """Resume a paused task."""
    result = await session.execute(select(ScheduledTask).where(ScheduledTask.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        return None
    task.status = TaskStatus.ACTIVE
    await session.commit()
    await session.refresh(task)
    return task


async def delete_task(session: AsyncSession, task_id: str) -> bool:
    """Delete a task. Returns True if found."""
    result = await session.execute(select(ScheduledTask).where(ScheduledTask.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        return False
    await session.delete(task)
    await session.commit()
    return True


async def record_run(
    session: AsyncSession,
    task_id: str,
    status: RunStatus,
    result_text: str | None = None,
    error_text: str | None = None,
) -> TaskRun:
    """Record a task execution."""
    run = TaskRun(
        task_id=task_id,
        status=status,
        result=result_text,
        error=error_text,
    )
    session.add(run)

    # Update the parent task
    task_result = await session.execute(select(ScheduledTask).where(ScheduledTask.id == task_id))
    task = task_result.scalar_one_or_none()
    if task:
        task.run_count += 1
        task.last_run_at = func.now()
        if task.max_runs and task.run_count >= task.max_runs:
            task.status = TaskStatus.COMPLETED

    await session.commit()
    await session.refresh(run)
    return run


async def list_runs(session: AsyncSession, task_id: str, limit: int = 20) -> list[TaskRun]:
    """List recent runs for a task."""
    result = await session.execute(
        select(TaskRun).where(TaskRun.task_id == task_id).order_by(TaskRun.started_at.desc()).limit(limit)
    )
    return list(result.scalars().all())
