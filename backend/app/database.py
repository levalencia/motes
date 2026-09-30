"""Async database engine and session factory."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings


def create_engine(settings: Settings):  # noqa: ANN201
    """Create an async SQLAlchemy engine."""
    return create_async_engine(
        settings.database_url,
        echo=settings.debug,
        pool_pre_ping=True,
    )


def create_session_factory(engine) -> async_sessionmaker[AsyncSession]:  # noqa: ANN001
    """Create an async session factory."""
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
