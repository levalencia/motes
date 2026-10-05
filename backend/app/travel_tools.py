"""Travel tools — flight and hotel search via Amadeus test API / web fallback.

Uses Amadeus Self-Service API (free test tier) for flights and hotels.
Set AMADEUS_API_KEY and AMADEUS_API_SECRET env vars, or falls back to
a DuckDuckGo web search for travel results.
"""

from __future__ import annotations

import json
import os

import httpx
import structlog

from app.tools import Tool

logger = structlog.get_logger()

AMADEUS_AUTH_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
AMADEUS_FLIGHT_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"
AMADEUS_HOTEL_URL = "https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-city"
DDG_URL = "https://html.duckduckgo.com/html/"


async def _get_amadeus_token(client: httpx.AsyncClient) -> str | None:
    """Get an Amadeus OAuth2 token."""
    key = os.environ.get("AMADEUS_API_KEY")
    secret = os.environ.get("AMADEUS_API_SECRET")
    if not key or not secret:
        return None
    resp = await client.post(
        AMADEUS_AUTH_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": key,
            "client_secret": secret,
        },
    )
    resp.raise_for_status()
    return resp.json().get("access_token")


class FlightSearchTool(Tool):
    """Search for flight offers between two airports."""

    name = "flight_search"
    description = (
        "Search for flights between two cities/airports. "
        "Returns available flight offers with prices, airlines, and durations. "
        "Requires origin, destination, and departure date."
    )
    parameters = {
        "type": "object",
        "properties": {
            "origin": {
                "type": "string",
                "description": "Origin airport IATA code (e.g., 'JFK', 'LAX', 'BRU')",
            },
            "destination": {
                "type": "string",
                "description": "Destination airport IATA code (e.g., 'CDG', 'LHR')",
            },
            "departure_date": {
                "type": "string",
                "description": "Departure date in YYYY-MM-DD format",
            },
            "return_date": {
                "type": "string",
                "description": "Return date in YYYY-MM-DD format (optional, for round trips)",
            },
            "adults": {
                "type": "integer",
                "description": "Number of adult passengers (default 1)",
            },
        },
        "required": ["origin", "destination", "departure_date"],
    }

    async def execute(self, arguments: dict) -> str:
        origin = arguments.get("origin", "").upper()
        destination = arguments.get("destination", "").upper()
        departure_date = arguments.get("departure_date", "")
        return_date = arguments.get("return_date")
        adults = arguments.get("adults", 1)

        if not origin or not destination or not departure_date:
            return json.dumps({"error": "origin, destination, and departure_date are required"})

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                token = await _get_amadeus_token(client)
                if token:
                    params = {
                        "originLocationCode": origin,
                        "destinationLocationCode": destination,
                        "departureDate": departure_date,
                        "adults": adults,
                        "max": 5,
                    }
                    if return_date:
                        params["returnDate"] = return_date
                    resp = await client.get(
                        AMADEUS_FLIGHT_URL,
                        params=params,
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    offers = []
                    for offer in data.get("data", [])[:5]:
                        itineraries = []
                        for itin in offer.get("itineraries", []):
                            segments = []
                            for seg in itin.get("segments", []):
                                segments.append(
                                    {
                                        "carrier": seg.get("carrierCode"),
                                        "flight": f"{seg.get('carrierCode')}{seg.get('number')}",
                                        "departure": seg.get("departure", {}).get("at"),
                                        "arrival": seg.get("arrival", {}).get("at"),
                                        "from": seg.get("departure", {}).get("iataCode"),
                                        "to": seg.get("arrival", {}).get("iataCode"),
                                    }
                                )
                            itineraries.append(
                                {
                                    "duration": itin.get("duration"),
                                    "segments": segments,
                                }
                            )
                        offers.append(
                            {
                                "price": offer.get("price", {}).get("total"),
                                "currency": offer.get("price", {}).get("currency"),
                                "itineraries": itineraries,
                            }
                        )
                    return json.dumps({"flights": offers, "source": "amadeus"})

                # Fallback: search suggestion
                query = f"flights from {origin} to {destination} on {departure_date}"
                return json.dumps(
                    {
                        "message": f"No Amadeus API key configured. Search '{query}' on a travel site for results.",
                        "suggestion": f"Try Skyscanner or Kayak for {origin}→{destination} on {departure_date}",
                        "source": "fallback",
                    }
                )
        except Exception as e:
            logger.warning("flight_search_error", error=str(e))
            return json.dumps({"error": str(e)})


class HotelSearchTool(Tool):
    """Search for hotels in a city."""

    name = "hotel_search"
    description = (
        "Search for hotels in a given city. "
        "Returns hotel names and locations. "
        "Uses Amadeus API if configured, otherwise provides search suggestions."
    )
    parameters = {
        "type": "object",
        "properties": {
            "city_code": {
                "type": "string",
                "description": "IATA city code (e.g., 'PAR' for Paris, 'NYC' for New York)",
            },
            "check_in": {
                "type": "string",
                "description": "Check-in date in YYYY-MM-DD format",
            },
            "check_out": {
                "type": "string",
                "description": "Check-out date in YYYY-MM-DD format",
            },
        },
        "required": ["city_code"],
    }

    async def execute(self, arguments: dict) -> str:
        city_code = arguments.get("city_code", "").upper()
        arguments.get("check_in", "")
        arguments.get("check_out", "")

        if not city_code:
            return json.dumps({"error": "city_code is required"})

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                token = await _get_amadeus_token(client)
                if token:
                    resp = await client.get(
                        AMADEUS_HOTEL_URL,
                        params={"cityCode": city_code},
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    hotels = []
                    for hotel in data.get("data", [])[:10]:
                        hotels.append(
                            {
                                "name": hotel.get("name"),
                                "hotel_id": hotel.get("hotelId"),
                                "latitude": hotel.get("geoCode", {}).get("latitude"),
                                "longitude": hotel.get("geoCode", {}).get("longitude"),
                            }
                        )
                    return json.dumps({"hotels": hotels, "city": city_code, "source": "amadeus"})

                # Fallback
                return json.dumps(
                    {
                        "message": "No Amadeus API key configured.",
                        "suggestion": f"Search for hotels in {city_code} on Booking.com, Hotels.com, or Expedia.",
                        "source": "fallback",
                    }
                )
        except Exception as e:
            logger.warning("hotel_search_error", error=str(e))
            return json.dumps({"error": str(e)})
