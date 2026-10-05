"""Todoist tools — list and create tasks via Todoist REST API.

Uses TODOIST_API_KEY env var for authentication.
"""

from __future__ import annotations

import json
import os

import httpx
import structlog

from app.tools import Tool

logger = structlog.get_logger()

TODOIST_API = "https://api.todoist.com/rest/v2"


def _todoist_headers() -> dict[str, str]:
    token = os.environ.get("TODOIST_API_KEY", "")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


class TodoistListTool(Tool):
    """List tasks from Todoist."""

    name = "todoist_list"
    description = (
        "List tasks from Todoist. Can filter by project or return all active tasks. "
        "Returns task content, due dates, priority, and labels. "
        "Requires TODOIST_API_KEY env var."
    )
    parameters = {
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "Filter by project ID (optional)",
            },
            "filter": {
                "type": "string",
                "description": "Todoist filter expression (e.g., 'today', 'overdue', 'p1')",
            },
            "limit": {
                "type": "integer",
                "description": "Max tasks to return (default: 20)",
            },
        },
        "required": [],
    }

    async def execute(self, arguments: dict) -> str:
        project_id = arguments.get("project_id")
        filter_expr = arguments.get("filter")
        limit = arguments.get("limit", 20)

        if not os.environ.get("TODOIST_API_KEY"):
            return json.dumps({"error": "TODOIST_API_KEY env var is required"})

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                params = {}
                if project_id:
                    params["project_id"] = project_id
                if filter_expr:
                    params["filter"] = filter_expr

                resp = await client.get(
                    f"{TODOIST_API}/tasks",
                    params=params,
                    headers=_todoist_headers(),
                )
                resp.raise_for_status()
                tasks = []
                for task in resp.json()[:limit]:
                    tasks.append(
                        {
                            "id": task.get("id"),
                            "content": task.get("content"),
                            "description": task.get("description"),
                            "priority": task.get("priority"),
                            "due": task.get("due", {}).get("string") if task.get("due") else None,
                            "due_date": task.get("due", {}).get("date") if task.get("due") else None,
                            "labels": task.get("labels", []),
                            "project_id": task.get("project_id"),
                            "url": task.get("url"),
                        }
                    )
                return json.dumps({"tasks": tasks, "count": len(tasks)})
        except Exception as e:
            logger.warning("todoist_list_error", error=str(e))
            return json.dumps({"error": str(e)})


class TodoistCreateTool(Tool):
    """Create a new task in Todoist."""

    name = "todoist_create"
    description = (
        "Create a new task in Todoist. "
        "Supports setting content, due date, priority, labels, and project. "
        "Requires TODOIST_API_KEY env var."
    )
    parameters = {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "Task title/content",
            },
            "description": {
                "type": "string",
                "description": "Task description (optional)",
            },
            "due_string": {
                "type": "string",
                "description": "Due date in natural language (e.g., 'tomorrow', 'next Monday', 'Jan 15')",
            },
            "due_date": {
                "type": "string",
                "description": "Due date in YYYY-MM-DD format",
            },
            "priority": {
                "type": "integer",
                "enum": [1, 2, 3, 4],
                "description": "Priority level: 1 (normal) to 4 (urgent)",
            },
            "labels": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Labels to apply",
            },
            "project_id": {
                "type": "string",
                "description": "Project ID to add the task to",
            },
        },
        "required": ["content"],
    }

    async def execute(self, arguments: dict) -> str:
        content = arguments.get("content", "")
        if not content:
            return json.dumps({"error": "content is required"})
        if not os.environ.get("TODOIST_API_KEY"):
            return json.dumps({"error": "TODOIST_API_KEY env var is required"})

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                payload = {"content": content}
                for key in ("description", "due_string", "due_date", "priority", "labels", "project_id"):
                    val = arguments.get(key)
                    if val is not None:
                        payload[key] = val

                resp = await client.post(
                    f"{TODOIST_API}/tasks",
                    json=payload,
                    headers=_todoist_headers(),
                )
                resp.raise_for_status()
                task = resp.json()
                return json.dumps(
                    {
                        "created": True,
                        "id": task.get("id"),
                        "content": task.get("content"),
                        "url": task.get("url"),
                    }
                )
        except Exception as e:
            logger.warning("todoist_create_error", error=str(e))
            return json.dumps({"error": str(e)})
