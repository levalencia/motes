"""Notion tools — search pages and read content via Notion API.

Uses NOTION_API_KEY env var for authentication.
"""

from __future__ import annotations

import json
import os

import httpx
import structlog

from app.tools import Tool

logger = structlog.get_logger()

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _notion_headers() -> dict[str, str]:
    token = os.environ.get("NOTION_API_KEY", "")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


class NotionSearchTool(Tool):
    """Search for pages and databases in Notion."""

    name = "notion_search"
    description = (
        "Search for pages and databases in your Notion workspace. "
        "Returns page titles, IDs, and URLs. "
        "Requires NOTION_API_KEY env var (integration token)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query text",
            },
            "filter_type": {
                "type": "string",
                "enum": ["page", "database"],
                "description": "Filter to only pages or databases (optional)",
            },
            "limit": {
                "type": "integer",
                "description": "Max results to return (default: 10)",
            },
        },
        "required": ["query"],
    }

    async def execute(self, arguments: dict) -> str:
        query = arguments.get("query", "")
        filter_type = arguments.get("filter_type")
        limit = arguments.get("limit", 10)

        if not query:
            return json.dumps({"error": "query is required"})
        if not os.environ.get("NOTION_API_KEY"):
            return json.dumps({"error": "NOTION_API_KEY env var is required"})

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                payload = {"query": query, "page_size": min(limit, 100)}
                if filter_type:
                    payload["filter"] = {"value": filter_type, "property": "object"}

                resp = await client.post(
                    f"{NOTION_API}/search",
                    json=payload,
                    headers=_notion_headers(),
                )
                resp.raise_for_status()
                data = resp.json()

                results = []
                for item in data.get("results", [])[:limit]:
                    obj_type = item.get("object")
                    title = ""
                    if obj_type == "page":
                        props = item.get("properties", {})
                        for prop in props.values():
                            if prop.get("type") == "title":
                                title_parts = prop.get("title", [])
                                title = "".join(t.get("plain_text", "") for t in title_parts)
                                break
                    elif obj_type == "database":
                        title_parts = item.get("title", [])
                        title = "".join(t.get("plain_text", "") for t in title_parts)

                    results.append({
                        "id": item.get("id"),
                        "type": obj_type,
                        "title": title,
                        "url": item.get("url"),
                        "last_edited": item.get("last_edited_time"),
                    })

                return json.dumps({"results": results, "count": len(results)})
        except Exception as e:
            logger.warning("notion_search_error", error=str(e))
            return json.dumps({"error": str(e)})


class NotionReadPageTool(Tool):
    """Read the content of a Notion page."""

    name = "notion_read_page"
    description = (
        "Read the content blocks of a Notion page by its ID. "
        "Returns text content from paragraphs, headings, lists, etc. "
        "Requires NOTION_API_KEY env var."
    )
    parameters = {
        "type": "object",
        "properties": {
            "page_id": {
                "type": "string",
                "description": "Notion page ID (UUID format)",
            },
        },
        "required": ["page_id"],
    }

    async def execute(self, arguments: dict) -> str:
        page_id = arguments.get("page_id", "")
        if not page_id:
            return json.dumps({"error": "page_id is required"})
        if not os.environ.get("NOTION_API_KEY"):
            return json.dumps({"error": "NOTION_API_KEY env var is required"})

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Get page metadata
                page_resp = await client.get(
                    f"{NOTION_API}/pages/{page_id}",
                    headers=_notion_headers(),
                )
                page_resp.raise_for_status()
                page_data = page_resp.json()

                # Get page title
                title = ""
                for prop in page_data.get("properties", {}).values():
                    if prop.get("type") == "title":
                        title = "".join(t.get("plain_text", "") for t in prop.get("title", []))
                        break

                # Get page content blocks
                blocks_resp = await client.get(
                    f"{NOTION_API}/blocks/{page_id}/children",
                    params={"page_size": 100},
                    headers=_notion_headers(),
                )
                blocks_resp.raise_for_status()
                blocks_data = blocks_resp.json()

                content = []
                for block in blocks_data.get("results", []):
                    block_type = block.get("type", "")
                    block_data = block.get(block_type, {})

                    # Extract text from rich_text arrays
                    rich_text = block_data.get("rich_text", [])
                    text = "".join(rt.get("plain_text", "") for rt in rich_text)

                    if text or block_type in ("divider", "table_of_contents"):
                        content.append({
                            "type": block_type,
                            "text": text,
                        })

                return json.dumps({
                    "page_id": page_id,
                    "title": title,
                    "url": page_data.get("url"),
                    "content": content,
                })
        except Exception as e:
            logger.warning("notion_read_page_error", error=str(e))
            return json.dumps({"error": str(e)})
