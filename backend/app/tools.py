"""Tool registry and built-in demo tools for the agent loop."""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from typing import Any, Protocol


class Tool(Protocol):
    """Protocol for agent-callable tools."""

    @property
    def name(self) -> str: ...

    @property
    def description(self) -> str: ...

    @property
    def parameters(self) -> dict[str, Any]: ...

    async def execute(self, arguments: dict[str, Any]) -> str: ...


class CurrentTimeTool:
    """Returns the current date and time in UTC."""

    name = "current_time"
    description = "Get the current date and time in UTC. No parameters needed."
    parameters: dict[str, Any] = {"type": "object", "properties": {}, "required": []}

    async def execute(self, arguments: dict[str, Any]) -> str:
        now = datetime.now(UTC)
        return json.dumps({
            "utc": now.isoformat(),
            "unix": int(now.timestamp()),
        })


class CalculatorTool:
    """Evaluates a mathematical expression safely."""

    name = "calculator"
    description = (
        "Evaluate a mathematical expression. "
        "Supports +, -, *, /, **, sqrt(), abs(), sin(), cos(), tan(), pi, e. "
        "Example: '2 * (3 + 4)' or 'sqrt(144)'"
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "The mathematical expression to evaluate",
            }
        },
        "required": ["expression"],
    }

    _SAFE_NAMES: dict[str, Any] = {
        "sqrt": math.sqrt,
        "abs": abs,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "pi": math.pi,
        "e": math.e,
        "log": math.log,
        "log10": math.log10,
        "pow": pow,
        "round": round,
    }

    async def execute(self, arguments: dict[str, Any]) -> str:
        expression = arguments.get("expression", "")
        if not expression:
            return json.dumps({"error": "No expression provided"})
        try:
            # Safe eval with restricted builtins
            result = eval(expression, {"__builtins__": {}}, self._SAFE_NAMES)  # noqa: S307
            return json.dumps({"expression": expression, "result": result})
        except Exception as exc:
            return json.dumps({"error": f"Cannot evaluate: {exc}"})


class ToolRegistry:
    """Registry of available tools for the agent."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        """List all registered tools."""
        return list(self._tools.values())

    def to_openai_tools(self) -> list[dict[str, Any]]:
        """Convert registered tools to OpenAI function-calling format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self._tools.values()
        ]


def create_default_registry() -> ToolRegistry:
    """Create a registry with built-in demo tools."""
    registry = ToolRegistry()
    registry.register(CurrentTimeTool())
    registry.register(CalculatorTool())
    return registry
