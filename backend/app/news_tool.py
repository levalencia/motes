"""News tool — fetch top headlines via DuckDuckGo news search.

No API key required. Uses DuckDuckGo's news search endpoint.
"""

from __future__ import annotations

import json
import re

import httpx
import structlog

from app.tools import Tool

logger = structlog.get_logger()

DDG_NEWS_URL = "https://duckduckgo.com/"
DDG_API_URL = "https://api.duckduckgo.com/"


class NewsTool(Tool):
    """Fetch latest news headlines on a topic."""

    name = "news"
    description = (
        "Get the latest news headlines on any topic. "
        "Uses DuckDuckGo news search — no API key required. "
        "Returns headline titles, sources, and URLs."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "News topic to search for (e.g., 'AI', 'stock market', 'climate change')",
            },
            "limit": {
                "type": "integer",
                "description": "Max number of headlines to return (default: 5)",
            },
        },
        "required": ["query"],
    }

    async def execute(self, arguments: dict) -> str:
        query = arguments.get("query", "")
        limit = arguments.get("limit", 5)

        if not query:
            return json.dumps({"error": "query is required"})

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                # Use DuckDuckGo instant answer API first
                resp = await client.get(
                    DDG_API_URL,
                    params={"q": query, "format": "json", "t": "MotesAssistant"},
                    headers={"User-Agent": "MotesAssistant/1.0"},
                )
                data = resp.json()

                articles = []

                # Try related topics from DDG
                for topic in data.get("RelatedTopics", [])[:limit]:
                    if "Text" in topic:
                        articles.append({
                            "title": topic.get("Text", "")[:200],
                            "url": topic.get("FirstURL", ""),
                        })

                # If DDG instant answer didn't provide enough, try HTML scraping
                if len(articles) < limit:
                    resp = await client.get(
                        "https://html.duckduckgo.com/html/",
                        params={"q": f"{query} news", "t": "h_", "ia": "news"},
                        headers={"User-Agent": "MotesAssistant/1.0"},
                    )
                    # Parse simple results from HTML
                    text = resp.text
                    # Extract result titles and URLs
                    result_pattern = re.compile(
                        r'class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>',
                        re.IGNORECASE,
                    )
                    for match in result_pattern.finditer(text):
                        url, title = match.group(1), match.group(2)
                        if title.strip():
                            articles.append({
                                "title": title.strip(),
                                "url": url,
                            })
                            if len(articles) >= limit:
                                break

                if not articles:
                    return json.dumps({
                        "message": f"No news found for '{query}'. Try a different search term.",
                        "query": query,
                    })

                return json.dumps({
                    "query": query,
                    "articles": articles[:limit],
                    "count": len(articles[:limit]),
                })
        except Exception as e:
            logger.warning("news_tool_error", error=str(e))
            return json.dumps({"error": str(e)})
