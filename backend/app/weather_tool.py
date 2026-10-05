"""Weather tool — current conditions and forecast via Open-Meteo (free, no API key).

Supports: current weather, 7-day forecast, by city name or coordinates.
Uses Open-Meteo geocoding + weather API — completely free, no rate limits.
"""

from __future__ import annotations

import json

import httpx
import structlog

from app.tools import Tool

logger = structlog.get_logger()

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight showers",
    81: "Moderate showers",
    82: "Violent showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class WeatherTool(Tool):
    """Get current weather and forecast for any location."""

    name = "weather"
    description = (
        "Get current weather conditions and 7-day forecast for a city or location. "
        "Returns temperature, humidity, wind, conditions, and daily forecast."
    )
    parameters = {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "City name (e.g., 'Brussels', 'Tokyo', 'New York')",
            },
            "latitude": {
                "type": "number",
                "description": "Latitude (optional, if known)",
            },
            "longitude": {
                "type": "number",
                "description": "Longitude (optional, if known)",
            },
        },
        "required": [],
    }

    async def execute(self, args: dict) -> str:
        location = args.get("location", "")
        lat = args.get("latitude")
        lon = args.get("longitude")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Geocode if needed
                if lat is None or lon is None:
                    if not location:
                        return json.dumps({"error": "Provide a location or coordinates"})
                    geo_resp = await client.get(
                        GEOCODE_URL,
                        params={"name": location, "count": 1, "language": "en"},
                    )
                    geo_data = geo_resp.json()
                    results = geo_data.get("results", [])
                    if not results:
                        return json.dumps({"error": f"Location '{location}' not found"})
                    lat = results[0]["latitude"]
                    lon = results[0]["longitude"]
                    location = f"{results[0]['name']}, {results[0].get('country', '')}"

                # Get weather
                resp = await client.get(
                    WEATHER_URL,
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "current": (
                            "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m"
                        ),
                        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum",
                        "timezone": "auto",
                        "forecast_days": 7,
                    },
                )
                data = resp.json()
                current = data.get("current", {})
                daily = data.get("daily", {})

                # Format current
                weather_code = current.get("weather_code", 0)
                result = {
                    "location": location,
                    "current": {
                        "temperature": f"{current.get('temperature_2m', '?')}°C",
                        "feels_like": f"{current.get('apparent_temperature', '?')}°C",
                        "humidity": f"{current.get('relative_humidity_2m', '?')}%",
                        "wind": f"{current.get('wind_speed_10m', '?')} km/h",
                        "conditions": WMO_CODES.get(weather_code, "Unknown"),
                    },
                    "forecast": [],
                }

                # Format forecast
                times = daily.get("time", [])
                for i, date in enumerate(times):
                    code = daily.get("weather_code", [0] * 7)[i]
                    result["forecast"].append(
                        {
                            "date": date,
                            "high": f"{daily.get('temperature_2m_max', [0] * 7)[i]}°C",
                            "low": f"{daily.get('temperature_2m_min', [0] * 7)[i]}°C",
                            "precipitation": f"{daily.get('precipitation_sum', [0] * 7)[i]}mm",
                            "conditions": WMO_CODES.get(code, "Unknown"),
                        }
                    )

                return json.dumps(result)
        except Exception as e:
            logger.warning("weather_tool_error", error=str(e))
            return json.dumps({"error": str(e)})
