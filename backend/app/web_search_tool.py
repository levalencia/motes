"""Web search tool — gives agents the ability to search the internet."""

from __future__ import annotations

import json
from typing import Any

import httpx


class WebSearchTool:
    """Search the web using Brave Search API or DuckDuckGo (free fallback)."""

    name = "web_search"
    description = (
        "Search the internet for current information. "
        "Use this for questions about recent events, prices, weather, news, "
        "or anything that requires up-to-date information."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query",
            },
            "max_results": {
                "type": "integer",
                "description": "Max results to return (default 5)",
            },
        },
        "required": ["query"],
    }

    def __init__(self, brave_api_key: str = "") -> None:
        self._brave_key = brave_api_key

    async def execute(self, arguments: dict[str, Any]) -> str:
        query = arguments.get("query", "")
        max_results = min(arguments.get("max_results", 5), 10)

        if not query:
            return json.dumps({"error": "No search query provided"})

        # Try Brave Search if API key available
        if self._brave_key:
            return await self._brave_search(query, max_results)

        # Free fallback: DuckDuckGo HTML (no API key needed)
        return await self._ddg_search(query, max_results)

    async def _brave_search(self, query: str, max_results: int) -> str:
        """Search using Brave Search API."""
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self._brave_key,
        }
        params = {"q": query, "count": max_results}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers, params=params)
                if resp.status_code != 200:
                    return json.dumps({"error": f"Brave Search error: HTTP {resp.status_code}"})
                data = resp.json()
                results = []
                for item in data.get("web", {}).get("results", [])[:max_results]:
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "description": item.get("description", ""),
                    })
                return json.dumps({"query": query, "results": results})
        except Exception as exc:
            return json.dumps({"error": f"Search error: {exc}"})

    async def _ddg_search(self, query: str, max_results: int) -> str:
        """Search using DuckDuckGo HTML (free, no API key)."""
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Motes Agent)"
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, data={"q": query}, headers=headers)
                if resp.status_code != 200:
                    return json.dumps({"error": f"DuckDuckGo error: HTTP {resp.status_code}"})

                # Parse HTML results (simple extraction)
                text = resp.text
                results = []
                # Find result blocks
                parts = text.split('class="result__a"')
                for part in parts[1:max_results + 1]:
                    title = ""
                    link = ""
                    snippet = ""
                    # Extract href
                    if 'href="' in part:
                        href_start = part.index('href="') + 6
                        href_end = part.index('"', href_start)
                        link = part[href_start:href_end]
                    # Extract title text
                    if ">" in part:
                        tag_end = part.index(">") + 1
                        close = part.find("</a>", tag_end)
                        if close > 0:
                            title = part[tag_end:close]
                            # Strip HTML tags
                            import re
                            title = re.sub(r"<[^>]+>", "", title).strip()
                    # Extract snippet
                    snippet_marker = 'class="result__snippet"'
                    if snippet_marker in part:
                        s_start = part.index(snippet_marker)
                        s_tag = part.index(">", s_start) + 1
                        s_end = part.find("</", s_tag)
                        if s_end > 0:
                            snippet = re.sub(r"<[^>]+>", "", part[s_tag:s_end]).strip()

                    if title or link:
                        results.append({
                            "title": title,
                            "url": link,
                            "description": snippet,
                        })

                return json.dumps({"query": query, "results": results})
        except Exception as exc:
            return json.dumps({"error": f"Search error: {exc}"})
