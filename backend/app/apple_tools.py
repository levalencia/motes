"""Apple tools — Reminders and Notes via AppleScript (macOS only).

Uses subprocess to call osascript for native macOS integration.
No API keys, no OAuth — works directly on the user's Mac.
"""

from __future__ import annotations

import json
import subprocess

import structlog

from app.tools import Tool

logger = structlog.get_logger()


def _run_applescript(script: str) -> str:
    """Execute an AppleScript and return stdout."""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "AppleScript failed")
    return result.stdout.strip()


class ReminderListTool(Tool):
    """List reminders from Apple Reminders."""

    name = "reminders_list"
    description = "List reminders from Apple Reminders. Optionally filter by list name."
    parameters = {
        "type": "object",
        "properties": {
            "list_name": {
                "type": "string",
                "description": "Reminder list name (e.g., 'Compras', 'Work'). Leave empty for all.",
            },
            "show_completed": {
                "type": "boolean",
                "description": "Include completed reminders (default: false)",
            },
        },
        "required": [],
    }

    async def execute(self, args: dict) -> str:
        list_name = args.get("list_name", "")

        try:
            if list_name:
                script = f'''
                    tell application "Reminders"
                        set output to ""
                        set targetList to list "{list_name}"
                        repeat with r in (reminders of targetList whose completed is false)
                            set output to output & name of r & " | " & (due date of r as string) & "\\n"
                        end repeat
                        return output
                    end tell
                '''
            else:
                script = '''
                    tell application "Reminders"
                        set output to ""
                        repeat with l in lists
                            set output to output & "📋 " & name of l & "\\n"
                            repeat with r in (reminders of l whose completed is false)
                                set output to output & "  • " & name of r & "\\n"
                            end repeat
                        end repeat
                        return output
                    end tell
                '''
            result = _run_applescript(script)
            return json.dumps({"reminders": result or "No reminders found"})
        except Exception as e:
            logger.warning("reminders_list_error", error=str(e))
            return json.dumps({"error": str(e)})


class ReminderCreateTool(Tool):
    """Create a new reminder in Apple Reminders."""

    name = "reminders_create"
    description = "Create a reminder in Apple Reminders with optional due date and list."
    parameters = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Reminder title"},
            "list_name": {
                "type": "string",
                "description": "List to add to (default: default list)",
            },
            "due_date": {
                "type": "string",
                "description": "Due date in natural format (e.g., '2026-10-01', 'tomorrow')",
            },
            "notes": {"type": "string", "description": "Additional notes"},
        },
        "required": ["title"],
    }

    async def execute(self, args: dict) -> str:
        title = args["title"]
        list_name = args.get("list_name", "")
        notes = args.get("notes", "")

        try:
            if list_name:
                script = f'''
                    tell application "Reminders"
                        tell list "{list_name}"
                            set newReminder to make new reminder with properties {{name:"{title}", body:"{notes}"}}
                        end tell
                        return "Created: {title} in {list_name}"
                    end tell
                '''
            else:
                script = f'''
                    tell application "Reminders"
                        set newReminder to make new reminder with properties {{name:"{title}", body:"{notes}"}}
                        return "Created: {title}"
                    end tell
                '''
            result = _run_applescript(script)
            return json.dumps({"result": result})
        except Exception as e:
            logger.warning("reminders_create_error", error=str(e))
            return json.dumps({"error": str(e)})


class NotesListTool(Tool):
    """List notes from Apple Notes."""

    name = "notes_list"
    description = "List notes from Apple Notes. Shows note titles and folders."
    parameters = {
        "type": "object",
        "properties": {
            "folder": {
                "type": "string",
                "description": "Folder name to filter (leave empty for all)",
            },
            "limit": {
                "type": "integer",
                "description": "Max notes to return (default: 20)",
            },
        },
        "required": [],
    }

    async def execute(self, args: dict) -> str:
        folder = args.get("folder", "")
        limit = args.get("limit", 20)

        try:
            if folder:
                script = f'''
                    tell application "Notes"
                        set output to ""
                        set i to 0
                        repeat with n in notes of folder "{folder}"
                            if i >= {limit} then exit repeat
                            set output to output & name of n & "\\n"
                            set i to i + 1
                        end repeat
                        return output
                    end tell
                '''
            else:
                script = f'''
                    tell application "Notes"
                        set output to ""
                        set i to 0
                        repeat with n in notes
                            if i >= {limit} then exit repeat
                            set output to output & name of n & "\\n"
                            set i to i + 1
                        end repeat
                        return output
                    end tell
                '''
            result = _run_applescript(script)
            return json.dumps({"notes": result or "No notes found"})
        except Exception as e:
            logger.warning("notes_list_error", error=str(e))
            return json.dumps({"error": str(e)})


class NotesReadTool(Tool):
    """Read a specific note from Apple Notes."""

    name = "notes_read"
    description = "Read the content of a specific note from Apple Notes by title."
    parameters = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Note title to read"},
        },
        "required": ["title"],
    }

    async def execute(self, args: dict) -> str:
        title = args["title"]
        try:
            script = f'''
                tell application "Notes"
                    set output to ""
                    repeat with n in notes
                        if name of n is "{title}" then
                            set output to plaintext of n
                            exit repeat
                        end if
                    end repeat
                    return output
                end tell
            '''
            result = _run_applescript(script)
            return json.dumps({"title": title, "content": result or "Note not found"})
        except Exception as e:
            logger.warning("notes_read_error", error=str(e))
            return json.dumps({"error": str(e)})
