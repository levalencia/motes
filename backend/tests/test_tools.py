"""Tests for the tool registry and built-in tools."""

import json

import pytest

from app.tools import CalculatorTool, CurrentTimeTool, ToolRegistry, create_default_registry


@pytest.mark.unit
class TestCurrentTimeTool:
    """Current time tool tests."""

    @pytest.mark.asyncio
    async def test_returns_utc(self) -> None:
        tool = CurrentTimeTool()
        result = json.loads(await tool.execute({}))
        assert "utc" in result
        assert "unix" in result
        assert isinstance(result["unix"], int)

    def test_metadata(self) -> None:
        tool = CurrentTimeTool()
        assert tool.name == "current_time"
        assert "UTC" in tool.description


@pytest.mark.unit
class TestCalculatorTool:
    """Calculator tool tests."""

    @pytest.mark.asyncio
    async def test_basic_math(self) -> None:
        tool = CalculatorTool()
        result = json.loads(await tool.execute({"expression": "2 + 3"}))
        assert result["result"] == 5

    @pytest.mark.asyncio
    async def test_complex_expression(self) -> None:
        tool = CalculatorTool()
        result = json.loads(await tool.execute({"expression": "sqrt(144)"}))
        assert result["result"] == 12.0

    @pytest.mark.asyncio
    async def test_invalid_expression(self) -> None:
        tool = CalculatorTool()
        result = json.loads(await tool.execute({"expression": "invalid"}))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_empty_expression(self) -> None:
        tool = CalculatorTool()
        result = json.loads(await tool.execute({}))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_no_dangerous_builtins(self) -> None:
        """Verify that dangerous builtins like __import__ are blocked."""
        tool = CalculatorTool()
        result = json.loads(
            await tool.execute({"expression": "__import__('os').system('echo hacked')"})
        )
        assert "error" in result


@pytest.mark.unit
class TestToolRegistry:
    """Tool registry tests."""

    def test_register_and_get(self) -> None:
        registry = ToolRegistry()
        tool = CurrentTimeTool()
        registry.register(tool)
        assert registry.get("current_time") is tool

    def test_get_missing_returns_none(self) -> None:
        registry = ToolRegistry()
        assert registry.get("nonexistent") is None

    def test_list_tools(self) -> None:
        registry = create_default_registry()
        tools = registry.list_tools()
        names = {t.name for t in tools}
        assert "current_time" in names
        assert "calculator" in names

    def test_openai_format(self) -> None:
        registry = create_default_registry()
        schemas = registry.to_openai_tools()
        assert len(schemas) == 2
        assert all(s["type"] == "function" for s in schemas)
        names = {s["function"]["name"] for s in schemas}
        assert names == {"current_time", "calculator"}
