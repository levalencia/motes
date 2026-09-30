"""Motes: FastAPI application factory and entrypoint."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import models so Base.metadata includes them
import app.approvals  # noqa: F401
import app.memory  # noqa: F401
import app.scheduler  # noqa: F401
import app.voice  # noqa: F401
from app.config import Settings, get_settings
from app.database import create_engine, create_session_factory
from app.logging import setup_logging
from app.models import Base
from app.observability import setup_otel

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown."""
    settings: Settings = app.state.settings

    # Structured logging
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

    logger.info(
        "motes_starting",
        app=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    try:
        yield
    finally:
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
    from app.routes.memory import router as memory_router
    from app.routes.providers import router as providers_router
    from app.routes.scheduler import router as scheduler_router
    from app.routes.voice import router as voice_router

    app.include_router(auth_router)
    app.include_router(providers_router)
    app.include_router(agents_router)
    app.include_router(chat_router)
    app.include_router(memory_router)
    app.include_router(approvals_router)
    app.include_router(scheduler_router)
    app.include_router(voice_router)

    return app


# Default app instance for uvicorn
app = create_app()
