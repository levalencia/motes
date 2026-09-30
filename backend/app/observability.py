"""OpenTelemetry setup for Motes.

Follows Archon patterns:
- Conditional init (only when otel_enabled=true)
- FastAPI + SQLAlchemy + httpx auto-instrumentation
- Custom spans for LLM calls and tool execution
- Graceful degradation when OTEL is disabled
"""

from __future__ import annotations

from typing import Any

import structlog

from app.config import Settings

logger = structlog.get_logger()

# Lazy references — only imported when OTEL is enabled
_tracer = None


def setup_otel(settings: Settings) -> None:
    """Initialize OpenTelemetry tracing if enabled."""
    global _tracer  # noqa: PLW0603

    if not settings.otel_enabled:
        logger.info("otel_disabled")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({
            "service.name": settings.otel_service_name,
            "service.version": settings.app_version,
        })

        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(
            endpoint=settings.otel_exporter_endpoint
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer("motes")

        logger.info(
            "otel_initialized",
            endpoint=settings.otel_exporter_endpoint,
            service=settings.otel_service_name,
        )
    except Exception:
        logger.warning("otel_init_failed", exc_info=True)


def instrument_app(app: Any) -> None:
    """Add auto-instrumentation to FastAPI app."""
    if _tracer is None:
        return

    try:
        from opentelemetry.instrumentation.fastapi import (
            FastAPIInstrumentor,
        )

        FastAPIInstrumentor.instrument_app(
            app,
            excluded_urls="health",
        )
        logger.info("otel_fastapi_instrumented")
    except Exception:
        logger.warning("otel_fastapi_instrument_failed", exc_info=True)

    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
        logger.info("otel_httpx_instrumented")
    except Exception:
        logger.warning("otel_httpx_instrument_failed", exc_info=True)


def get_tracer():
    """Get the OTEL tracer (or None if disabled)."""
    return _tracer


def trace_llm_call(
    provider: str, model: str, input_tokens: int = 0, output_tokens: int = 0
):
    """Create a span for an LLM call."""
    if _tracer is None:
        return _NullSpan()
    span = _tracer.start_span(
        "gen_ai.chat",
        attributes={
            "gen_ai.operation.name": "chat",
            "gen_ai.request.model": model,
            "gen_ai.system": provider,
            "gen_ai.usage.input_tokens": input_tokens,
            "gen_ai.usage.output_tokens": output_tokens,
        },
    )
    return span


def trace_tool_call(tool_name: str):
    """Create a span for a tool execution."""
    if _tracer is None:
        return _NullSpan()
    return _tracer.start_span(
        f"tool.{tool_name}",
        attributes={"tool.name": tool_name},
    )


class _NullSpan:
    """No-op context manager when OTEL is disabled."""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def set_attribute(self, *args):
        pass

    def end(self):
        pass
