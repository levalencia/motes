"""TDD tests for the scheduled tasks system."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Agent, Provider, User
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

pytestmark = pytest.mark.unit


@pytest.fixture
async def user(session: AsyncSession) -> User:
    u = User(username="scheduler_tester", password_hash="hash")
    session.add(u)
    await session.commit()
    await session.refresh(u)
    return u


@pytest.fixture
async def provider(session: AsyncSession, user: User) -> Provider:
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
    a = Agent(
        user_id=user.id,
        provider_id=provider.id,
        name="scheduler-agent",
    )
    session.add(a)
    await session.commit()
    await session.refresh(a)
    return a


async def test_create_scheduled_task(session: AsyncSession, agent: Agent) -> None:
    """User creates a recurring task."""
    task = await create_task(
        session,
        agent_id=agent.id,
        name="Daily summary",
        prompt="Summarize my emails from today",
        cron_expression="0 9 * * *",
    )
    assert task.id is not None
    assert task.agent_id == agent.id
    assert task.name == "Daily summary"
    assert task.prompt == "Summarize my emails from today"
    assert task.cron_expression == "0 9 * * *"
    assert task.status == TaskStatus.ACTIVE
    assert task.run_count == 0


async def test_task_executes_and_records_run(session: AsyncSession, agent: Agent) -> None:
    """Task run is recorded with result."""
    task = await create_task(
        session,
        agent.id,
        "Check weather",
        "What's the weather?",
        "0 8 * * *",
    )
    run = await record_run(
        session,
        task.id,
        RunStatus.COMPLETED,
        result_text="Sunny, 72°F",
    )
    assert run.task_id == task.id
    assert run.status == RunStatus.COMPLETED
    assert run.result == "Sunny, 72°F"

    # Verify task updated
    tasks = await list_tasks(session, agent.id)
    updated = [t for t in tasks if t.id == task.id][0]
    assert updated.run_count == 1


async def test_task_saves_result_to_thread(session: AsyncSession, agent: Agent) -> None:
    """Task result appears in run history (thread equivalent)."""
    task = await create_task(
        session,
        agent.id,
        "News digest",
        "Top news today",
        "0 7 * * *",
    )
    await record_run(session, task.id, RunStatus.COMPLETED, result_text="Top stories...")
    await record_run(session, task.id, RunStatus.COMPLETED, result_text="More stories...")

    runs = await list_runs(session, task.id)
    assert len(runs) == 2
    # Runs are ordered desc by started_at
    results = [r.result for r in runs]
    assert "Top stories..." in results
    assert "More stories..." in results


async def test_list_tasks(session: AsyncSession, agent: Agent) -> None:
    """API returns user's tasks for a given agent."""
    await create_task(session, agent.id, "Task A", "Prompt A", "0 9 * * *")
    await create_task(session, agent.id, "Task B", "Prompt B", "0 10 * * *")
    await create_task(session, agent.id, "Task C", "Prompt C", "0 11 * * *")

    tasks = await list_tasks(session, agent.id)
    assert len(tasks) == 3
    names = {t.name for t in tasks}
    assert names == {"Task A", "Task B", "Task C"}


async def test_delete_task(session: AsyncSession, agent: Agent) -> None:
    """Remove a task."""
    task = await create_task(session, agent.id, "Temp task", "Do something", "once")
    assert await delete_task(session, task.id) is True

    tasks = await list_tasks(session, agent.id)
    assert len(tasks) == 0


async def test_delete_nonexistent_task(session: AsyncSession) -> None:
    """Deleting a nonexistent task returns False."""
    assert await delete_task(session, "nonexistent-id") is False


async def test_pause_and_resume_task(session: AsyncSession, agent: Agent) -> None:
    """Task can be paused and resumed."""
    task = await create_task(session, agent.id, "Pausable", "Do it", "0 9 * * *")

    paused = await pause_task(session, task.id)
    assert paused is not None
    assert paused.status == TaskStatus.PAUSED

    resumed = await resume_task(session, task.id)
    assert resumed is not None
    assert resumed.status == TaskStatus.ACTIVE


async def test_task_completes_after_max_runs(session: AsyncSession, agent: Agent) -> None:
    """Task with max_runs auto-completes after reaching limit."""
    task = await create_task(
        session,
        agent.id,
        "One-shot",
        "Do once",
        "once",
        max_runs=2,
    )
    await record_run(session, task.id, RunStatus.COMPLETED, result_text="Run 1")
    await record_run(session, task.id, RunStatus.COMPLETED, result_text="Run 2")

    tasks = await list_tasks(session, agent.id)
    completed = [t for t in tasks if t.id == task.id][0]
    assert completed.status == TaskStatus.COMPLETED
    assert completed.run_count == 2


async def test_record_failed_run(session: AsyncSession, agent: Agent) -> None:
    """Failed task run records error."""
    task = await create_task(session, agent.id, "Failing", "Fail", "0 9 * * *")
    run = await record_run(
        session,
        task.id,
        RunStatus.FAILED,
        error_text="Connection timeout",
    )
    assert run.status == RunStatus.FAILED
    assert run.error == "Connection timeout"
