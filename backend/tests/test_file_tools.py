"""Tests for file tools — filesystem access."""

import json

import pytest

from app.file_tools import (
    FileListTool,
    FileReadTool,
    FileSearchTool,
    _human_size,
)

pytestmark = pytest.mark.unit


class TestHumanSize:
    def test_bytes(self):
        assert _human_size(500) == "500.0 B"

    def test_kilobytes(self):
        assert "KB" in _human_size(2048)

    def test_megabytes(self):
        assert "MB" in _human_size(2 * 1024 * 1024)


class TestFileListTool:
    @pytest.mark.asyncio
    async def test_list_home(self, tmp_path):
        tool = FileListTool(str(tmp_path))
        (tmp_path / "test.txt").write_text("hello")
        result = json.loads(await tool.execute({"path": str(tmp_path)}))
        assert result["total"] >= 1
        assert any(e["name"] == "test.txt" for e in result["entries"])

    @pytest.mark.asyncio
    async def test_list_with_pattern(self, tmp_path):
        tool = FileListTool(str(tmp_path))
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.py").write_text("b")
        result = json.loads(await tool.execute({"path": str(tmp_path), "pattern": "*.txt"}))
        assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_path_outside_base(self, tmp_path):
        tool = FileListTool(str(tmp_path))
        result = json.loads(await tool.execute({"path": "/etc"}))
        assert "error" in result


class TestFileReadTool:
    @pytest.mark.asyncio
    async def test_read_file(self, tmp_path):
        tool = FileReadTool(str(tmp_path))
        f = tmp_path / "test.txt"
        f.write_text("line1\nline2\nline3")
        result = json.loads(await tool.execute({"path": str(f)}))
        assert result["total_lines"] == 3
        assert "line1" in result["content"]

    @pytest.mark.asyncio
    async def test_read_nonexistent(self, tmp_path):
        tool = FileReadTool(str(tmp_path))
        result = json.loads(await tool.execute({"path": str(tmp_path / "nope.txt")}))
        assert "error" in result


class TestFileSearchTool:
    @pytest.mark.asyncio
    async def test_search_by_name(self, tmp_path):
        tool = FileSearchTool(str(tmp_path))
        (tmp_path / "report.pdf").write_text("x")
        (tmp_path / "other.txt").write_text("y")
        result = json.loads(await tool.execute({"query": "report", "path": str(tmp_path)}))
        assert result["total_found"] >= 1
        assert any("report" in r["name"] for r in result["results"])

    @pytest.mark.asyncio
    async def test_search_with_extension(self, tmp_path):
        tool = FileSearchTool(str(tmp_path))
        (tmp_path / "a.pdf").write_text("x")
        (tmp_path / "a.txt").write_text("y")
        result = json.loads(await tool.execute({"query": "a", "extension": ".pdf", "path": str(tmp_path)}))
        assert all(r["name"].endswith(".pdf") for r in result["results"])
