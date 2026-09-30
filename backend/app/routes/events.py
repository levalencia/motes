"""SSE endpoint for pushing proactive notifications to active chat sessions."""

from __future__ import annotations

import json

import structlog
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from app.auth import decode_jwt

logger = structlog.get_logger()

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("/stream")
async def event_stream(request: Request, token: str):
    """SSE stream for real-time proactive notifications.

    Client connects with: EventSource('/api/events/stream?token=...')
    Receives events like:
        data: {"type": "notification", "title": "📧 New email", "body": "..."}
    """
    settings = request.app.state.settings
    payload = decode_jwt(token, settings.secret_key)
    if not payload:
        return EventSourceResponse(
            _error_gen("Invalid token"), media_type="text/event-stream"
        )

    user_id = payload["sub"]
    event_bus = request.app.state.event_bus

    async def generate():
        subscription = event_bus.subscribe(user_id)
        try:
            while True:
                if await request.is_disconnected():
                    break
                event = await subscription.get(timeout=30.0)
                if event is not None:
                    yield {
                        "event": "notification",
                        "data": json.dumps({
                            "type": "notification",
                            "title": event.title,
                            "body": event.body,
                            "category": event.category,
                            "agent_id": event.agent_id,
                        }),
                    }
                else:
                    # Send keepalive
                    yield {"event": "keepalive", "data": ""}
        finally:
            subscription.close()

    return EventSourceResponse(generate())


async def _error_gen(msg: str):
    yield {"event": "error", "data": json.dumps({"error": msg})}
