"""Spotify tools — search tracks and control playback via Spotify Web API.

Uses SPOTIFY_TOKEN env var (OAuth2 Bearer token) for authentication.
"""

from __future__ import annotations

import json
import os

import httpx
import structlog

from app.tools import Tool

logger = structlog.get_logger()

SPOTIFY_API = "https://api.spotify.com/v1"


def _spotify_headers() -> dict[str, str]:
    token = os.environ.get("SPOTIFY_TOKEN", "")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


class SpotifySearchTool(Tool):
    """Search for tracks, artists, or albums on Spotify."""

    name = "spotify_search"
    description = (
        "Search Spotify for tracks, artists, albums, or playlists. "
        "Returns names, artists, album art, and Spotify URIs. "
        "Requires SPOTIFY_TOKEN env var."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (e.g., 'Bohemian Rhapsody', 'Taylor Swift')",
            },
            "type": {
                "type": "string",
                "enum": ["track", "artist", "album", "playlist"],
                "description": "Type of content to search for (default: track)",
            },
            "limit": {
                "type": "integer",
                "description": "Max results to return (default: 5)",
            },
        },
        "required": ["query"],
    }

    async def execute(self, arguments: dict) -> str:
        query = arguments.get("query", "")
        search_type = arguments.get("type", "track")
        limit = arguments.get("limit", 5)

        if not query:
            return json.dumps({"error": "query is required"})
        if not os.environ.get("SPOTIFY_TOKEN"):
            return json.dumps({"error": "SPOTIFY_TOKEN env var is required"})

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{SPOTIFY_API}/search",
                    params={"q": query, "type": search_type, "limit": limit},
                    headers=_spotify_headers(),
                )
                resp.raise_for_status()
                data = resp.json()

                results = []
                items_key = f"{search_type}s"
                for item in data.get(items_key, {}).get("items", [])[:limit]:
                    result = {
                        "name": item.get("name"),
                        "uri": item.get("uri"),
                        "url": item.get("external_urls", {}).get("spotify"),
                    }
                    if search_type == "track":
                        result["artists"] = [a.get("name") for a in item.get("artists", [])]
                        result["album"] = item.get("album", {}).get("name")
                        result["duration_ms"] = item.get("duration_ms")
                    elif search_type == "artist":
                        result["genres"] = item.get("genres", [])
                        result["followers"] = item.get("followers", {}).get("total")
                    elif search_type == "album":
                        result["artists"] = [a.get("name") for a in item.get("artists", [])]
                        result["total_tracks"] = item.get("total_tracks")
                        result["release_date"] = item.get("release_date")
                    results.append(result)

                return json.dumps({"results": results, "type": search_type, "count": len(results)})
        except Exception as e:
            logger.warning("spotify_search_error", error=str(e))
            return json.dumps({"error": str(e)})


class SpotifyPlayTool(Tool):
    """Control Spotify playback — play, pause, skip."""

    name = "spotify_play"
    description = (
        "Control Spotify playback: play a track/album/playlist by URI, "
        "pause, resume, skip to next/previous. "
        "Requires SPOTIFY_TOKEN env var with appropriate scopes."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["play", "pause", "next", "previous", "resume"],
                "description": "Playback action to perform",
            },
            "uri": {
                "type": "string",
                "description": "Spotify URI to play (e.g., 'spotify:track:...'). Required for 'play' action.",
            },
        },
        "required": ["action"],
    }

    async def execute(self, arguments: dict) -> str:
        action = arguments.get("action", "")
        uri = arguments.get("uri", "")

        if not os.environ.get("SPOTIFY_TOKEN"):
            return json.dumps({"error": "SPOTIFY_TOKEN env var is required"})

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                headers = _spotify_headers()

                if action == "play":
                    payload = {}
                    if uri:
                        if uri.startswith("spotify:track:"):
                            payload["uris"] = [uri]
                        else:
                            payload["context_uri"] = uri
                    resp = await client.put(
                        f"{SPOTIFY_API}/me/player/play",
                        json=payload if payload else None,
                        headers=headers,
                    )
                elif action == "pause":
                    resp = await client.put(f"{SPOTIFY_API}/me/player/pause", headers=headers)
                elif action == "resume":
                    resp = await client.put(f"{SPOTIFY_API}/me/player/play", headers=headers)
                elif action == "next":
                    resp = await client.post(f"{SPOTIFY_API}/me/player/next", headers=headers)
                elif action == "previous":
                    resp = await client.post(f"{SPOTIFY_API}/me/player/previous", headers=headers)
                else:
                    return json.dumps({"error": f"Unknown action: {action}"})

                if resp.status_code in (200, 202, 204):
                    return json.dumps({"success": True, "action": action})
                else:
                    return json.dumps({"error": f"Spotify returned {resp.status_code}: {resp.text}"})
        except Exception as e:
            logger.warning("spotify_play_error", error=str(e))
            return json.dumps({"error": str(e)})
