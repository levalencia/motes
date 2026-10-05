"""Local filesystem tools — browse, read, edit, and send files from the host machine.

Gives the agent access to the user's local files. This is the equivalent of
OpenAI Dots' "local computer access" but accessible remotely via Tailscale/VPN.
"""

from __future__ import annotations

import json
import mimetypes
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _safe_path(base: str, requested: str) -> Path:
    """Resolve path safely within base directory."""
    base_path = Path(base).expanduser().resolve()
    requested_path = Path(requested).expanduser().resolve()
    # Allow access to home directory and below
    if not str(requested_path).startswith(str(base_path)):
        raise ValueError(f"Access denied: path outside {base_path}")
    return requested_path


class FileListTool:
    """List files in a directory with details."""

    name = "file_list"
    description = (
        "List files and folders in a directory on the user's computer. "
        "Returns name, size, modified date, and type for each entry. "
        "Default directory is the user's home folder."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory path (default: home folder). Use ~ for home.",
            },
            "pattern": {
                "type": "string",
                "description": "Filter by glob pattern (e.g. '*.pptx', '*.pdf')",
            },
            "sort_by": {
                "type": "string",
                "description": "Sort by: 'modified' (newest first), 'name', 'size'",
            },
        },
        "required": [],
    }

    def __init__(self, base_dir: str = "~") -> None:
        self._base = str(Path(base_dir).expanduser().resolve())

    async def execute(self, arguments: dict[str, Any]) -> str:
        path_str = arguments.get("path", "~")
        pattern = arguments.get("pattern", "")
        sort_by = arguments.get("sort_by", "modified")

        try:
            target = _safe_path(self._base, path_str)
        except ValueError as e:
            return json.dumps({"error": str(e)})

        if not target.exists():
            return json.dumps({"error": f"Path not found: {target}"})
        if not target.is_dir():
            return json.dumps({"error": f"Not a directory: {target}"})

        entries = []
        items = list(target.glob(pattern)) if pattern else list(target.iterdir())

        for item in items:
            if item.name.startswith("."):
                continue  # skip hidden files
            try:
                stat = item.stat()
                entries.append(
                    {
                        "name": item.name,
                        "path": str(item),
                        "type": "folder" if item.is_dir() else "file",
                        "size_bytes": stat.st_size if item.is_file() else 0,
                        "size_human": _human_size(stat.st_size) if item.is_file() else "",
                        "modified": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
                    }
                )
            except (PermissionError, OSError):
                continue

        if sort_by == "modified":
            entries.sort(key=lambda e: e["modified"], reverse=True)
        elif sort_by == "size":
            entries.sort(key=lambda e: e["size_bytes"], reverse=True)
        else:
            entries.sort(key=lambda e: e["name"].lower())

        return json.dumps(
            {
                "directory": str(target),
                "entries": entries[:50],
                "total": len(entries),
            }
        )


class FileReadTool:
    """Read the content of a text file."""

    name = "file_read"
    description = (
        "Read the content of a text file on the user's computer. "
        "Works with .txt, .md, .py, .json, .csv, .yaml, and other text formats. "
        "For binary files (pptx, docx, xlsx), use file_inspect instead."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to read"},
            "max_lines": {
                "type": "integer",
                "description": "Max lines to return (default 100)",
            },
        },
        "required": ["path"],
    }

    def __init__(self, base_dir: str = "~") -> None:
        self._base = str(Path(base_dir).expanduser().resolve())

    async def execute(self, arguments: dict[str, Any]) -> str:
        path_str = arguments.get("path", "")
        max_lines = min(arguments.get("max_lines", 100), 500)

        try:
            target = _safe_path(self._base, path_str)
        except ValueError as e:
            return json.dumps({"error": str(e)})

        if not target.exists():
            return json.dumps({"error": f"File not found: {target}"})
        if not target.is_file():
            return json.dumps({"error": f"Not a file: {target}"})

        try:
            content = target.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()
            return json.dumps(
                {
                    "path": str(target),
                    "content": "\n".join(lines[:max_lines]),
                    "total_lines": len(lines),
                    "truncated": len(lines) > max_lines,
                }
            )
        except Exception as e:
            return json.dumps({"error": f"Read error: {e}"})


class FileSearchTool:
    """Search for files by name or content."""

    name = "file_search"
    description = (
        "Search for files on the user's computer by name pattern. "
        "Finds the most recently modified files matching the pattern. "
        "Example: 'presentation' finds all files with 'presentation' in the name."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search term (matches filename, case-insensitive)",
            },
            "extension": {
                "type": "string",
                "description": "File extension filter (e.g. '.pptx', '.pdf', '.docx')",
            },
            "path": {
                "type": "string",
                "description": "Directory to search in (default: home)",
            },
        },
        "required": ["query"],
    }

    def __init__(self, base_dir: str = "~") -> None:
        self._base = str(Path(base_dir).expanduser().resolve())

    async def execute(self, arguments: dict[str, Any]) -> str:
        query = arguments.get("query", "").lower()
        extension = arguments.get("extension", "")
        path_str = arguments.get("path", "~")

        try:
            target = _safe_path(self._base, path_str)
        except ValueError as e:
            return json.dumps({"error": str(e)})

        results = []
        try:
            for item in target.rglob("*"):
                if item.is_file() and query in item.name.lower():
                    if extension and not item.name.lower().endswith(extension.lower()):
                        continue
                    if any(p.startswith(".") for p in item.parts):
                        continue
                    try:
                        stat = item.stat()
                        results.append(
                            {
                                "name": item.name,
                                "path": str(item),
                                "size_human": _human_size(stat.st_size),
                                "modified": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
                            }
                        )
                    except (PermissionError, OSError):
                        continue
                if len(results) >= 200:
                    break
        except (PermissionError, OSError):
            pass

        results.sort(key=lambda r: r["modified"], reverse=True)
        return json.dumps(
            {
                "query": query,
                "results": results[:20],
                "total_found": len(results),
            }
        )


class PptxInspectTool:
    """Inspect and read PowerPoint presentations."""

    name = "pptx_inspect"
    description = (
        "Read the content of a PowerPoint (.pptx) file. "
        "Returns slide titles, text content, and slide count. "
        "Can also show details of a specific slide."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the .pptx file"},
            "slide_number": {
                "type": "integer",
                "description": "Specific slide number to inspect (1-indexed). Omit for all slides.",
            },
        },
        "required": ["path"],
    }

    def __init__(self, base_dir: str = "~") -> None:
        self._base = str(Path(base_dir).expanduser().resolve())

    async def execute(self, arguments: dict[str, Any]) -> str:
        from pptx import Presentation

        path_str = arguments.get("path", "")
        slide_num = arguments.get("slide_number")

        try:
            target = _safe_path(self._base, path_str)
        except ValueError as e:
            return json.dumps({"error": str(e)})

        if not target.exists():
            return json.dumps({"error": f"File not found: {target}"})

        try:
            prs = Presentation(str(target))
            slides = []
            for i, slide in enumerate(prs.slides, 1):
                if slide_num and i != slide_num:
                    continue
                texts = []
                title = ""
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        text = shape.text_frame.text.strip()
                        if text:
                            texts.append(text)
                    if shape.shape_type == 13:  # Title
                        title = shape.text_frame.text.strip() if shape.has_text_frame else ""
                if not title and texts:
                    title = texts[0][:80]
                slides.append(
                    {
                        "slide_number": i,
                        "title": title,
                        "text_content": "\n".join(texts),
                    }
                )

            return json.dumps(
                {
                    "path": str(target),
                    "total_slides": len(prs.slides),
                    "slides": slides,
                }
            )
        except Exception as e:
            return json.dumps({"error": f"PPTX read error: {e}"})


class PptxAddSlideTool:
    """Add a new slide to a PowerPoint presentation."""

    name = "pptx_add_slide"
    description = (
        "Add a new slide to an existing PowerPoint (.pptx) file. Provide the title and body text for the new slide."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the .pptx file"},
            "title": {"type": "string", "description": "Slide title"},
            "body": {"type": "string", "description": "Slide body text"},
            "layout": {
                "type": "integer",
                "description": "Slide layout index (0=title, 1=title+content, default 1)",
            },
        },
        "required": ["path", "title"],
    }

    def __init__(self, base_dir: str = "~") -> None:
        self._base = str(Path(base_dir).expanduser().resolve())

    async def execute(self, arguments: dict[str, Any]) -> str:
        from pptx import Presentation

        path_str = arguments.get("path", "")
        title = arguments.get("title", "")
        body = arguments.get("body", "")
        layout_idx = arguments.get("layout", 1)

        try:
            target = _safe_path(self._base, path_str)
        except ValueError as e:
            return json.dumps({"error": str(e)})

        try:
            prs = Presentation(str(target)) if target.exists() else Presentation()

            layout = prs.slide_layouts[min(layout_idx, len(prs.slide_layouts) - 1)]
            slide = prs.slides.add_slide(layout)

            if slide.placeholders:
                if len(slide.placeholders) > 0:
                    slide.placeholders[0].text = title
                if len(slide.placeholders) > 1 and body:
                    slide.placeholders[1].text = body

            prs.save(str(target))
            return json.dumps(
                {
                    "status": "slide_added",
                    "path": str(target),
                    "slide_number": len(prs.slides),
                    "title": title,
                    "total_slides": len(prs.slides),
                }
            )
        except Exception as e:
            return json.dumps({"error": f"PPTX write error: {e}"})


class FileDownloadUrlTool:
    """Generate a download URL for a local file (for sending/sharing)."""

    name = "file_download_url"
    description = (
        "Make a local file available for download via a temporary URL. "
        "Use this when the user wants to download or email a file. "
        "Returns a URL that can be opened in a browser or attached to an email."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file"},
        },
        "required": ["path"],
    }

    def __init__(self, base_dir: str = "~") -> None:
        self._base = str(Path(base_dir).expanduser().resolve())

    async def execute(self, arguments: dict[str, Any]) -> str:
        path_str = arguments.get("path", "")

        try:
            target = _safe_path(self._base, path_str)
        except ValueError as e:
            return json.dumps({"error": str(e)})

        if not target.exists() or not target.is_file():
            return json.dumps({"error": f"File not found: {target}"})

        stat = target.stat()
        mime = mimetypes.guess_type(str(target))[0] or "application/octet-stream"

        return json.dumps(
            {
                "path": str(target),
                "filename": target.name,
                "size_human": _human_size(stat.st_size),
                "mime_type": mime,
                "download_url": f"/api/files/download?path={target}",
            }
        )


def _human_size(size: int) -> str:
    """Convert bytes to human-readable size."""
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
