"""Structured logging setup for Motes.

Follows Archon/Cogentrex patterns:
- structlog with correlation IDs via ContextVar
- PII/credential redaction processor
- JSON in production, colored console in development
- Module-level logger = structlog.get_logger() everywhere
"""

from __future__ import annotations

import re
from contextvars import ContextVar
from typing import Any

import structlog

# ── Correlation ID ContextVar ─────────────────────────────────────

correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Get the current correlation ID."""
    return correlation_id_ctx.get()


# ── Structlog Processors ─────────────────────────────────────────

SENSITIVE_KEYS = frozenset({
    "password", "secret", "token", "api_key", "apikey",
    "authorization", "cookie", "access_token", "refresh_token",
    "client_secret", "private_key", "credential",
})

SENSITIVE_PATTERNS = [
    re.compile(r"(sk-[a-zA-Z0-9]{20,})"),
    re.compile(r"(eyJ[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{20,})"),
    re.compile(r"([a-zA-Z0-9]{32,})"),
]


def _is_sensitive_key(key: str) -> bool:
    """Check if a key name suggests sensitive data."""
    lower = key.lower().replace("-", "_")
    return any(s in lower for s in SENSITIVE_KEYS)


def redact_event(
    _logger: Any, _method: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Redact sensitive values from log events."""
    for key, value in list(event_dict.items()):
        if isinstance(value, str) and _is_sensitive_key(key):
            event_dict[key] = "***REDACTED***"
    return event_dict


def add_correlation_id(
    _logger: Any, _method: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Inject correlation ID into every log event."""
    cid = correlation_id_ctx.get()
    if cid:
        event_dict["correlation_id"] = cid
    return event_dict


# ── Setup ─────────────────────────────────────────────────────────


def setup_logging(*, json_format: bool = False, log_level: str = "INFO") -> None:
    """Configure structlog for the application.

    Args:
        json_format: True for JSON output (production), False for console.
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR).
    """
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        add_correlation_id,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        redact_event,
    ]

    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(
            structlog.dev.ConsoleRenderer(colors=True)
        )

    level_map = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}
    level_number = level_map.get(log_level.upper(), 20)

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level_number),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
