"""Vision tool — analyze images using the LLM's vision capabilities.

Supports Anthropic (Claude) and OpenAI vision APIs.
The agent calls this tool when it needs to understand an image.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import httpx
import structlog

from app.tools import Tool

logger = structlog.get_logger()


def build_anthropic_vision_message(image_url: str, question: str) -> dict:
    """Build an Anthropic-format message with image content block."""
    # If it's a local URL, read the file and base64 encode
    if image_url.startswith("/uploads/"):
        filepath = Path("uploads") / image_url.split("/uploads/")[-1]
        if filepath.exists():
            data = filepath.read_bytes()
            b64 = base64.b64encode(data).decode()
            media_type = "image/jpeg"
            if filepath.suffix == ".png":
                media_type = "image/png"
            elif filepath.suffix == ".gif":
                media_type = "image/gif"
            elif filepath.suffix == ".webp":
                media_type = "image/webp"
            return {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64,
                        },
                    },
                    {"type": "text", "text": question},
                ],
            }

    # Remote URL
    return {
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {"type": "url", "url": image_url},
            },
            {"type": "text", "text": question},
        ],
    }


def build_openai_vision_message(image_url: str, question: str) -> dict:
    """Build an OpenAI-format message with image_url content."""
    if image_url.startswith("/uploads/"):
        filepath = Path("uploads") / image_url.split("/uploads/")[-1]
        if filepath.exists():
            data = filepath.read_bytes()
            b64 = base64.b64encode(data).decode()
            media_type = "image/jpeg"
            if filepath.suffix == ".png":
                media_type = "image/png"
            image_url = f"data:{media_type};base64,{b64}"

    return {
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": image_url}},
            {"type": "text", "text": question},
        ],
    }


class VisionTool(Tool):
    """Analyze images using the LLM's vision capabilities."""

    def __init__(
        self,
        provider_url: str,
        api_key: str,
        model: str,
        api_format: str = "anthropic",
    ) -> None:
        self._provider_url = provider_url
        self._api_key = api_key
        self._model = model
        self._api_format = api_format

    @property
    def name(self) -> str:
        return "analyze_image"

    @property
    def description(self) -> str:
        return (
            "Analyze an image to understand its contents. "
            "Can identify objects, read text, describe scenes, "
            "analyze receipts, documents, screenshots, photos, etc. "
            "Provide the image URL and a question about the image."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "URL of the image to analyze (local /uploads/... or remote https://...)",
                },
                "question": {
                    "type": "string",
                    "description": "What to analyze or ask about the image",
                },
            },
            "required": ["image_url", "question"],
        }

    async def execute(self, arguments: dict[str, Any]) -> str:
        image_url = arguments.get("image_url", "")
        question = arguments.get("question", "Describe this image in detail")

        try:
            if self._api_format == "anthropic":
                return await self._call_anthropic(image_url, question)
            else:
                return await self._call_openai(image_url, question)
        except Exception as exc:
            logger.warning("vision_tool_error", error=str(exc))
            return json.dumps({"error": f"Vision analysis failed: {exc}"})

    async def _call_anthropic(self, image_url: str, question: str) -> str:
        msg = build_anthropic_vision_message(image_url, question)

        async with httpx.AsyncClient(timeout=30) as client:
            # Strip trailing /v1 if present to avoid /v1/v1/messages
            base = self._provider_url.rstrip("/")
            url = f"{base}/messages" if base.endswith("/v1") else f"{base}/v1/messages"

            response = await client.post(
                url,
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self._model,
                    "max_tokens": 1024,
                    "messages": [msg],
                },
            )

        if response.status_code != 200:
            logger.warning("vision_api_error", status=response.status_code, body=response.text[:300])
            return json.dumps({"error": f"Vision API error: {response.text[:200]}"})

        data = response.json()
        text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")

        return json.dumps({"description": text})

    async def _call_openai(self, image_url: str, question: str) -> str:
        msg = build_openai_vision_message(image_url, question)

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self._provider_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "max_tokens": 1024,
                    "messages": [msg],
                },
            )

        if response.status_code != 200:
            logger.warning("vision_api_error", status=response.status_code, body=response.text[:300])
            return json.dumps({"error": f"Vision API error: {response.text[:200]}"})

        data = response.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return json.dumps({"description": text})
