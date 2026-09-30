"""Shared test fixtures."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure all models are registered with Base.metadata
import app.app_settings  # noqa: F401
import app.approvals  # noqa: F401
import app.mcp_connector  # noqa: F401
import app.memory  # noqa: F401
import app.oauth  # noqa: F401
import app.proactive  # noqa: F401
import app.scheduler  # noqa: F401
import app.voice  # noqa: F401
from app.config import Settings
from app.models import Base


@pytest.fixture
def settings() -> Settings:
    """Test settings with SQLite in-memory."""
    return Settings(
        debug=True,
        database_url="sqlite+aiosqlite:///:memory:",
        secret_key="test-secret-key-for-tests",
    )


@pytest.fixture
async def engine():
    """Async SQLite engine for tests."""
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session(engine) -> AsyncSession:
    """Async database session for tests."""
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess
