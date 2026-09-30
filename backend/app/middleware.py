"""Middleware for Motes — correlation IDs, request logging."""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.logging import correlation_id_ctx


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Assign a unique correlation ID to every request."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        cid = request.headers.get("x-correlation-id", str(uuid.uuid4()))
        correlation_id_ctx.set(cid)
        response = await call_next(request)
        response.headers["x-correlation-id"] = cid
        return response
