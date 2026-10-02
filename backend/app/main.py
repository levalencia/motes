"""Motes: FastAPI application factory and entrypoint."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import models so Base.metadata includes them
import app.app_settings  # noqa: F401
import app.approvals  # noqa: F401
import app.mcp_connector  # noqa: F401
import app.memory  # noqa: F401
import app.oauth  # noqa: F401
import app.proactive  # noqa: F401
import app.scheduler  # noqa: F401
import app.voice  # noqa: F401
from app.config import Settings, get_settings
from app.database import create_engine, create_session_factory
from app.logging import setup_logging
from app.models import Base
from app.observability import instrument_app, setup_otel

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown."""
    settings: Settings = app.state.settings

    setup_logging(
        json_format=not settings.debug,
        log_level="DEBUG" if settings.debug else "INFO",
    )

    # OpenTelemetry
    setup_otel(settings)

    # Database
    engine = create_engine(settings)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)

    # Create tables (dev convenience — production uses Alembic)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Event bus for real-time proactive notifications
    from app.event_bus import EventBus

    app.state.event_bus = EventBus()

    # Load saved service keys into environment
    from app.app_settings import get_setting
    from app.routes.service_keys import SERVICE_ENV_MAP

    async with app.state.session_factory() as key_session:
        for _svc, env_vars in SERVICE_ENV_MAP.items():
            for var in env_vars:
                val = await get_setting(key_session, f"service_key:{var}")
                if val:
                    os.environ[var] = val

    logger.info(
        "motes_starting",
        app=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    if not settings.secret_key:
        import secrets

        settings.__dict__["secret_key"] = secrets.token_hex(32)
        logger.warning(
            "motes_secret_key_generated",
            hint="Set MOTES_SECRET_KEY env var for production",
        )

    try:
        # Start background scanner
        from app.background_scanner import run_scanner

        scanner_task = asyncio.create_task(
            run_scanner(app.state.session_factory, app.state.event_bus)
        )

        # Start task scheduler
        from app.task_runner import run_task_scheduler

        task_scheduler_task = asyncio.create_task(
            run_task_scheduler(app.state.session_factory, app.state.event_bus)
        )
        yield
    finally:
        scanner_task.cancel()
        task_scheduler_task.cancel()
        await engine.dispose()
        logger.info("motes_shutdown")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory. Accepts optional settings for testing."""
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Open-source, model-agnostic personal AI agents",
        lifespan=lifespan,
    )
    app.state.settings = settings

    # Middleware
    from app.middleware import CorrelationIdMiddleware

    app.add_middleware(CorrelationIdMiddleware)

    # OTEL auto-instrumentation
    instrument_app(app)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health endpoint
    @app.get("/health")
    async def health() -> dict[str, str]:
        """Liveness probe."""
        return {
            "status": "ok",
            "app": settings.app_name,
            "version": settings.app_version,
        }

    # API routes
    from app.routes.agents import router as agents_router
    from app.routes.approvals import router as approvals_router
    from app.routes.auth import router as auth_router
    from app.routes.chat import router as chat_router
    from app.routes.events import router as events_router
    from app.routes.files import router as files_router
    from app.routes.mcp import router as mcp_router
    from app.routes.memory import router as memory_router
    from app.routes.notifications import router as notifications_router
    from app.routes.oauth import router as oauth_router
    from app.routes.providers import router as providers_router

    # Realtime voice call (Azure OpenAI Realtime API)
    from app.routes.realtime_call import router as realtime_call_router
    from app.routes.scheduler import router as scheduler_router
    from app.routes.service_keys import router as service_keys_router
    from app.routes.voice import router as voice_router
    from app.routes.voice_call import router as voice_call_router
    from app.routes.webhooks import router as webhooks_router

    app.include_router(auth_router)
    app.include_router(providers_router)
    app.include_router(agents_router)
    app.include_router(chat_router)
    app.include_router(events_router)
    app.include_router(files_router)
    app.include_router(memory_router)
    app.include_router(approvals_router)
    app.include_router(scheduler_router)
    app.include_router(service_keys_router)
    app.include_router(voice_router)
    app.include_router(mcp_router)
    app.include_router(oauth_router)
    app.include_router(notifications_router)
    app.include_router(voice_call_router)
    app.include_router(realtime_call_router)
    app.include_router(webhooks_router)

    return app


# Default app instance for uvicorn
app = create_app()
