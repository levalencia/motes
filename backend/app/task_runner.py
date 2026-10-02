"""Task runner — background loop that executes scheduled tasks based on cron expressions.

Runs every 60 seconds, checks which tasks are due, executes them via the agent loop,
and saves results to the unified thread.
"""

from __future__ import annotations

import asyncio
import contextlib
from datetime import UTC, datetime
from typing import Any

import structlog
from croniter import croniter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import selectinload

from app.models import Agent, Message
from app.scheduler import RunStatus, ScheduledTask, TaskStatus, record_run
from app.thread import get_or_create_thread

logger = structlog.get_logger()

TASK_CHECK_INTERVAL = 60  # seconds


async def run_task_scheduler(
    session_factory: async_sessionmaker,
    event_bus: Any = None,
) -> None:
    """Background loop: check and run due scheduled tasks."""
    logger.info("task_scheduler_started", interval=TASK_CHECK_INTERVAL)

    while True:
        try:
            async with session_factory() as session:
                # Get all active tasks with their agent + provider
                result = await session.execute(
                    select(ScheduledTask)
                    .where(ScheduledTask.status == TaskStatus.ACTIVE)
                )
                tasks = result.scalars().all()

                now = datetime.now(UTC)

                for task in tasks:
                    try:
                        # Check if task is due
                        if not _is_due(task, now):
                            continue

                        logger.info(
                            "task_executing",
                            task_id=task.id,
                            name=task.name,
                            cron=task.cron_expression,
                        )

                        # Get agent with provider
                        agent_result = await session.execute(
                            select(Agent)
                            .where(Agent.id == task.agent_id)
                            .options(selectinload(Agent.provider))
                        )
                        agent = agent_result.scalar_one_or_none()
                        if not agent or not agent.provider:
                            logger.warning("task_skip_no_provider", task_id=task.id)
                            continue

                        # Run the task prompt through the agent
                        response = await _run_task_prompt(
                            session, agent, task.prompt,
                        )

                        # Save result to thread
                        thread = await get_or_create_thread(session, task.agent_id)
                        session.add(Message(
                            conversation_id=thread.id,
                            role="assistant",
                            content=f"⏰ **{task.name}**\n\n{response}",
                            message_type="scheduled",
                        ))
                        await session.commit()

                        # Record run
                        await record_run(
                            session, task.id, RunStatus.COMPLETED,
                            result_text=response[:500],
                        )

                        # Push to event bus
                        if event_bus is not None:
                            from app.event_bus import ProactiveEvent

                            await event_bus.publish(ProactiveEvent(
                                user_id=agent.user_id,
                                agent_id=agent.id,
                                title=f"⏰ {task.name}",
                                body=response[:300],
                            ))

                        logger.info("task_completed", task_id=task.id, name=task.name)

                    except Exception:
                        logger.warning("task_run_error", task_id=task.id, exc_info=True)
                        with contextlib.suppress(Exception):
                            await record_run(
                                session, task.id, RunStatus.FAILED,
                                error_text="Execution failed",
                            )

        except Exception:
            logger.warning("task_scheduler_cycle_error", exc_info=True)

        await asyncio.sleep(TASK_CHECK_INTERVAL)


def _is_due(task: ScheduledTask, now: datetime) -> bool:
    """Check if a task should run now based on its cron expression."""
    try:
        cron = croniter(task.cron_expression, now)
        prev_time = cron.get_prev(datetime)
        # Task is due if the previous cron time is after the last run
        if task.last_run_at is None:
            return True
        return prev_time > task.last_run_at.replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return False


async def _run_task_prompt(
    session: Any,
    agent: Agent,
    prompt: str,
) -> str:
    """Run a prompt through the agent and return the text response."""
    from app.services import build_tool_registry

    provider = agent.provider
    tools = await build_tool_registry(session, agent.user_id)

    messages = [{"role": "user", "content": prompt}]

    if getattr(provider, "api_format", "openai") == "anthropic":
        from app.agent_loop_anthropic import run_anthropic_stream

        response = ""
        async for event in run_anthropic_stream(
            base_url=provider.base_url,
            api_key=provider.api_key_encrypted,
            model=provider.model,
            messages=messages,
            tools=tools,
            system_prompt=agent.system_prompt or "",
            temperature=0.5,
            max_tokens=1000,
        ):
            if event["type"] == "done":
                response = event["content"]
            elif event["type"] == "error":
                raise RuntimeError(event["message"])
    else:
        from app.agent_loop import run_agent_sync

        response = await run_agent_sync(
            base_url=provider.base_url,
            api_key=provider.api_key_encrypted,
            model=provider.model,
            messages=messages,
            tools=tools,
            temperature=0.5,
            max_tokens=1000,
        )

    return response or "Task completed (no output)"
