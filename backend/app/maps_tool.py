"""Maps tool — geocoding, place search, and directions via OpenStreetMap.

Uses OSM Nominatim (free, no API key) for geocoding/place search
and OSRM (free, no API key) for routing/directions.
"""

from __future__ import annotations

import json

import httpx
import structlog

from app.tools import Tool

logger = structlog.get_logger()

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
OSRM_URL = "https://router.project-osrm.org/route/v1/driving"
USER_AGENT = "MotesAssistant/1.0"


class MapsTool(Tool):
    """Geocode places, search locations, and get driving directions."""

    name = "maps"
    description = (
        "Search for places, geocode addresses, and get driving directions. "
        "Can find locations by name, get coordinates, calculate distances, "
        "and provide turn-by-turn driving directions between two points."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["search", "directions", "reverse_geocode"],
                "description": "Action: search, directions, or reverse_geocode",
            },
            "query": {
                "type": "string",
                "description": "Place name or address to search (for 'search' action)",
            },
            "origin": {
                "type": "string",
                "description": "Origin address or 'lat,lon' (for 'directions' action)",
            },
            "destination": {
                "type": "string",
                "description": "Destination address or 'lat,lon' (for 'directions' action)",
            },
            "latitude": {
                "type": "number",
                "description": "Latitude (for 'reverse_geocode' action)",
            },
            "longitude": {
                "type": "number",
                "description": "Longitude (for 'reverse_geocode' action)",
            },
        },
        "required": ["action"],
    }

    async def _geocode(self, client: httpx.AsyncClient, query: str) -> dict | None:
        """Geocode a place name to coordinates."""
        resp = await client.get(
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": USER_AGENT},
        )
        results = resp.json()
        if results:
            return {
                "lat": float(results[0]["lat"]),
                "lon": float(results[0]["lon"]),
                "display_name": results[0].get("display_name", ""),
            }
        return None

    async def execute(self, arguments: dict) -> str:
        action = arguments.get("action", "search")

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                if action == "search":
                    query = arguments.get("query", "")
                    if not query:
                        return json.dumps({"error": "query is required for search"})
                    resp = await client.get(
                        NOMINATIM_URL,
                        params={"q": query, "format": "json", "limit": 5, "addressdetails": 1},
                        headers={"User-Agent": USER_AGENT},
                    )
                    results = resp.json()
                    places = []
                    for r in results:
                        places.append(
                            {
                                "name": r.get("display_name"),
                                "latitude": float(r.get("lat", 0)),
                                "longitude": float(r.get("lon", 0)),
                                "type": r.get("type"),
                                "category": r.get("class"),
                            }
                        )
                    return json.dumps({"places": places, "count": len(places)})

                elif action == "directions":
                    origin_str = arguments.get("origin", "")
                    dest_str = arguments.get("destination", "")
                    if not origin_str or not dest_str:
                        return json.dumps({"error": "origin and destination are required for directions"})

                    # Try to parse as lat,lon or geocode
                    if "," in origin_str:
                        parts = origin_str.split(",")
                        try:
                            origin_coords = {"lat": float(parts[0]), "lon": float(parts[1])}
                        except ValueError:
                            origin_coords = await self._geocode(client, origin_str)
                    else:
                        origin_coords = await self._geocode(client, origin_str)

                    if "," in dest_str:
                        parts = dest_str.split(",")
                        try:
                            dest_coords = {"lat": float(parts[0]), "lon": float(parts[1])}
                        except ValueError:
                            dest_coords = await self._geocode(client, dest_str)
                    else:
                        dest_coords = await self._geocode(client, dest_str)

                    if not origin_coords or not dest_coords:
                        return json.dumps({"error": "Could not geocode origin or destination"})

                    # OSRM routing
                    o, d = origin_coords, dest_coords
                    coords_str = f"{o['lon']},{o['lat']};{d['lon']},{d['lat']}"
                    resp = await client.get(
                        f"{OSRM_URL}/{coords_str}",
                        params={"overview": "false", "steps": "true"},
                        headers={"User-Agent": USER_AGENT},
                    )
                    data = resp.json()
                    if data.get("code") != "Ok":
                        return json.dumps({"error": f"Routing failed: {data.get('message', 'unknown')}"})

                    route = data["routes"][0]
                    steps = []
                    for leg in route.get("legs", []):
                        for step in leg.get("steps", []):
                            maneuver = step.get("maneuver", {})
                            steps.append(
                                {
                                    "instruction": step.get("name", ""),
                                    "distance_m": step.get("distance"),
                                    "duration_s": step.get("duration"),
                                    "maneuver": maneuver.get("type"),
                                    "modifier": maneuver.get("modifier"),
                                }
                            )

                    return json.dumps(
                        {
                            "distance_km": round(route["distance"] / 1000, 1),
                            "duration_min": round(route["duration"] / 60, 1),
                            "steps": steps,
                        }
                    )

                elif action == "reverse_geocode":
                    lat = arguments.get("latitude")
                    lon = arguments.get("longitude")
                    if lat is None or lon is None:
                        return json.dumps({"error": "latitude and longitude required for reverse_geocode"})
                    resp = await client.get(
                        NOMINATIM_REVERSE_URL,
                        params={"lat": lat, "lon": lon, "format": "json"},
                        headers={"User-Agent": USER_AGENT},
                    )
                    data = resp.json()
                    return json.dumps(
                        {
                            "address": data.get("display_name"),
                            "details": data.get("address", {}),
                        }
                    )

                else:
                    return json.dumps({"error": f"Unknown action: {action}"})

        except Exception as e:
            logger.warning("maps_tool_error", error=str(e))
            return json.dumps({"error": str(e)})
