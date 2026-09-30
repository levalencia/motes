"""Structured logging setup with structlog."""

from __future__ import annotations

import structlog


def setup_logging(*, json_format: bool = True, log_level: str = "INFO") -> None:
    """Configure structlog for the application."""
    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    level_number = structlog._log_levels.NAME_TO_LEVEL.get(log_level.lower(), 20)

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level_number),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
