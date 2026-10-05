"""Home Assistant tools — list devices and control entities via HA REST API.

Uses HA_URL and HA_TOKEN env vars for authentication.
"""

from __future__ import annotations

import json
import os

import httpx
import structlog

from app.tools import Tool

logger = structlog.get_logger()


def _ha_url() -> str:
    return os.environ.get("HA_URL", "http://homeassistant.local:8123").rstrip("/")


def _ha_headers() -> dict[str, str]:
    token = os.environ.get("HA_TOKEN", "")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


class HAListDevicesTool(Tool):
    """List Home Assistant entities/devices and their states."""

    name = "ha_list_devices"
    description = (
        "List Home Assistant entities and their current states. "
        "Can filter by domain (light, switch, sensor, climate, etc.). "
        "Requires HA_URL and HA_TOKEN env vars."
    )
    parameters = {
        "type": "object",
        "properties": {
            "domain": {
                "type": "string",
                "description": "Filter by entity domain (e.g., 'light', 'switch', 'sensor', 'climate', 'media_player')",
            },
            "limit": {
                "type": "integer",
                "description": "Max entities to return (default: 20)",
            },
        },
        "required": [],
    }

    async def execute(self, arguments: dict) -> str:
        domain = arguments.get("domain")
        limit = arguments.get("limit", 20)

        if not os.environ.get("HA_TOKEN"):
            return json.dumps({"error": "HA_TOKEN env var is required"})

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{_ha_url()}/api/states",
                    headers=_ha_headers(),
                )
                resp.raise_for_status()
                entities = resp.json()

                results = []
                for entity in entities:
                    entity_id = entity.get("entity_id", "")
                    if domain and not entity_id.startswith(f"{domain}."):
                        continue
                    results.append(
                        {
                            "entity_id": entity_id,
                            "state": entity.get("state"),
                            "friendly_name": entity.get("attributes", {}).get("friendly_name"),
                            "last_changed": entity.get("last_changed"),
                        }
                    )
                    if len(results) >= limit:
                        break

                return json.dumps({"entities": results, "count": len(results)})
        except Exception as e:
            logger.warning("ha_list_devices_error", error=str(e))
            return json.dumps({"error": str(e)})


class HAControlDeviceTool(Tool):
    """Control a Home Assistant entity — turn on/off, set values."""

    name = "ha_control_device"
    description = (
        "Control a Home Assistant entity: turn on/off lights, switches, "
        "set thermostat temperature, etc. "
        "Requires HA_URL and HA_TOKEN env vars."
    )
    parameters = {
        "type": "object",
        "properties": {
            "entity_id": {
                "type": "string",
                "description": "Entity ID (e.g., 'light.living_room', 'switch.fan')",
            },
            "action": {
                "type": "string",
                "enum": ["turn_on", "turn_off", "toggle", "set_temperature"],
                "description": "Action to perform on the entity",
            },
            "brightness": {
                "type": "integer",
                "description": "Brightness 0-255 (for lights, with turn_on action)",
            },
            "temperature": {
                "type": "number",
                "description": "Target temperature (for climate entities, with set_temperature action)",
            },
            "color_name": {
                "type": "string",
                "description": "Color name (e.g., 'red', 'blue') for lights",
            },
        },
        "required": ["entity_id", "action"],
    }

    async def execute(self, arguments: dict) -> str:
        entity_id = arguments.get("entity_id", "")
        action = arguments.get("action", "")

        if not entity_id or not action:
            return json.dumps({"error": "entity_id and action are required"})
        if not os.environ.get("HA_TOKEN"):
            return json.dumps({"error": "HA_TOKEN env var is required"})

        try:
            domain = entity_id.split(".")[0]
            service = action

            # Build service data
            service_data = {"entity_id": entity_id}
            if arguments.get("brightness") is not None:
                service_data["brightness"] = arguments["brightness"]
            if arguments.get("temperature") is not None:
                service_data["temperature"] = arguments["temperature"]
            if arguments.get("color_name"):
                service_data["color_name"] = arguments["color_name"]

            # Special handling for set_temperature
            if action == "set_temperature":
                domain = "climate"
                service = "set_temperature"

            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{_ha_url()}/api/services/{domain}/{service}",
                    json=service_data,
                    headers=_ha_headers(),
                )
                resp.raise_for_status()

                return json.dumps(
                    {
                        "success": True,
                        "entity_id": entity_id,
                        "action": action,
                    }
                )
        except Exception as e:
            logger.warning("ha_control_device_error", error=str(e))
            return json.dumps({"error": str(e)})
