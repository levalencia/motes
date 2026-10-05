"""Scheduled tasks tool — lets the agent manage background tasks via chat.

The user can say things like:
- "what background tasks do I have?"
- "pause the weather task"
- "add a task: check my stocks every morning at 9am"
- "delete the news task"
"""

from __future__ import annotations

import json
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.scheduler import (
    create_task,
    delete_task,
    list_tasks,
    pause_task,
    resume_task,
)
from app.tools import Tool

logger = structlog.get_logger()


class ScheduledTasksTool(Tool):
    """Manage scheduled background tasks."""

    @property
    def name(self) -> str:
        return "scheduled_tasks"

    @property
    def description(self) -> str:
        return (
            "Manage scheduled background tasks. Actions: "
            "'list' (show all tasks), "
            "'create' (new task with name, prompt, cron_expression), "
            "'pause' (pause a task by id), "
            "'resume' (resume a paused task by id), "
            "'delete' (delete a task by id). "
            "Common cron expressions: "
            "'0 8 * * *' (daily 8am), '0 9 * * 1-5' (weekdays 9am), "
            "'0 19 * * *' (daily 7pm), '*/30 * * * *' (every 30min), "
            "'0 * * * *' (every hour)."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "create", "pause", "resume", "delete"],
                    "description": "Action to perform",
                },
                "task_id": {
                    "type": "string",
                    "description": "Task ID (for pause/resume/delete)",
                },
                "name": {
                    "type": "string",
                    "description": "Task name (for create)",
                },
                "prompt": {
                    "type": "string",
                    "description": "What the agent should do (for create)",
                },
                "cron_expression": {
                    "type": "string",
                    "description": "Cron schedule (for create)",
                },
            },
            "required": ["action"],
        }

    def __init__(self, session: AsyncSession, agent_id: str):
        self._session = session
        self._agent_id = agent_id

    async def execute(self, arguments: dict[str, Any]) -> str:
        action = arguments.get("action", "list")

        if action == "list":
            tasks = await list_tasks(self._session, self._agent_id)
            if not tasks:
                return json.dumps({"tasks": [], "message": "No scheduled tasks"})
            return json.dumps(
                {
                    "tasks": [
                        {
                            "id": t.id,
                            "name": t.name,
                            "prompt": t.prompt,
                            "cron_expression": t.cron_expression,
                            "status": t.status,
                            "run_count": t.run_count,
                        }
                        for t in tasks
                    ]
                }
            )

        elif action == "create":
            name = arguments.get("name", "")
            prompt = arguments.get("prompt", "")
            cron = arguments.get("cron_expression", "")
            if not prompt or not cron:
                return json.dumps({"error": "prompt and cron_expression required"})
            if not name:
                name = prompt[:50]
            task = await create_task(
                self._session,
                self._agent_id,
                name,
                prompt,
                cron,
            )
            return json.dumps(
                {
                    "created": True,
                    "id": task.id,
                    "name": task.name,
                    "cron_expression": task.cron_expression,
                }
            )

        elif action == "pause":
            task_id = arguments.get("task_id", "")
            if not task_id:
                return json.dumps({"error": "task_id required"})
            result = await pause_task(self._session, task_id)
            if result:
                return json.dumps({"paused": True, "name": result.name})
            return json.dumps({"error": "Task not found"})

        elif action == "resume":
            task_id = arguments.get("task_id", "")
            if not task_id:
                return json.dumps({"error": "task_id required"})
            result = await resume_task(self._session, task_id)
            if result:
                return json.dumps({"resumed": True, "name": result.name})
            return json.dumps({"error": "Task not found"})

        elif action == "delete":
            task_id = arguments.get("task_id", "")
            if not task_id:
                return json.dumps({"error": "task_id required"})
            deleted = await delete_task(self._session, task_id)
            return json.dumps({"deleted": deleted})

        return json.dumps({"error": f"Unknown action: {action}"})
