"""Tests for the task scheduler."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.scheduler import (
    RunStatus,
    TaskStatus,
    create_task,
    delete_task,
    list_runs,
    list_tasks,
    pause_task,
    record_run,
    resume_task,
)


@pytest.mark.unit
class TestScheduledTasks:
    """Scheduled task CRUD tests."""

    @pytest.mark.asyncio
    async def test_create_task(self, session: AsyncSession) -> None:
        task = await create_task(
            session, "agent-1", "Daily summary",
            "Summarize my emails", "0 9 * * *",
        )
        assert task.name == "Daily summary"
        assert task.status == TaskStatus.ACTIVE
        assert task.run_count == 0

    @pytest.mark.asyncio
    async def test_list_tasks(self, session: AsyncSession) -> None:
        await create_task(session, "agent-1", "Task A", "prompt", "0 9 * * *")
        await create_task(session, "agent-1", "Task B", "prompt", "0 18 * * *")
        tasks = await list_tasks(session, "agent-1")
        assert len(tasks) == 2

    @pytest.mark.asyncio
    async def test_pause_and_resume(self, session: AsyncSession) -> None:
        task = await create_task(
            session, "agent-1", "Task", "prompt", "0 9 * * *"
        )
        paused = await pause_task(session, task.id)
        assert paused is not None
        assert paused.status == TaskStatus.PAUSED

        resumed = await resume_task(session, task.id)
        assert resumed is not None
        assert resumed.status == TaskStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_delete_task(self, session: AsyncSession) -> None:
        task = await create_task(
            session, "agent-1", "Temp", "prompt", "once"
        )
        assert await delete_task(session, task.id) is True
        assert await delete_task(session, task.id) is False

    @pytest.mark.asyncio
    async def test_pause_nonexistent(self, session: AsyncSession) -> None:
        assert await pause_task(session, "fake") is None


@pytest.mark.unit
class TestTaskRuns:
    """Task run recording tests."""

    @pytest.mark.asyncio
    async def test_record_run(self, session: AsyncSession) -> None:
        task = await create_task(
            session, "agent-1", "Task", "prompt", "0 9 * * *"
        )
        run = await record_run(
            session, task.id, RunStatus.COMPLETED, result_text="Done"
        )
        assert run.status == RunStatus.COMPLETED
        assert run.result == "Done"

    @pytest.mark.asyncio
    async def test_run_increments_count(self, session: AsyncSession) -> None:
        task = await create_task(
            session, "agent-1", "Task", "prompt", "0 9 * * *"
        )
        await record_run(session, task.id, RunStatus.COMPLETED)
        await record_run(session, task.id, RunStatus.COMPLETED)
        # Refresh to see updated count
        from sqlalchemy import select

        from app.scheduler import ScheduledTask
        result = await session.execute(
            select(ScheduledTask).where(ScheduledTask.id == task.id)
        )
        updated = result.scalar_one()
        assert updated.run_count == 2

    @pytest.mark.asyncio
    async def test_max_runs_completes_task(self, session: AsyncSession) -> None:
        task = await create_task(
            session, "agent-1", "Once", "prompt", "once", max_runs=1
        )
        await record_run(session, task.id, RunStatus.COMPLETED)
        from sqlalchemy import select

        from app.scheduler import ScheduledTask
        result = await session.execute(
            select(ScheduledTask).where(ScheduledTask.id == task.id)
        )
        updated = result.scalar_one()
        assert updated.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_list_runs(self, session: AsyncSession) -> None:
        task = await create_task(
            session, "agent-1", "Task", "prompt", "0 9 * * *"
        )
        await record_run(session, task.id, RunStatus.COMPLETED, "R1")
        await record_run(session, task.id, RunStatus.FAILED, error_text="Err")
        runs = await list_runs(session, task.id)
        assert len(runs) == 2
        statuses = {r.status for r in runs}
        assert RunStatus.COMPLETED in statuses
        assert RunStatus.FAILED in statuses
