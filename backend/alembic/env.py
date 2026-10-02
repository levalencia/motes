"""Alembic env.py — sync migration runner for Motes.

Uses the sync psycopg2/psycopg driver (postgresql://) configured in alembic.ini,
NOT the async asyncpg driver used at runtime.
"""

from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

# Import ALL model modules so Base.metadata has every table
import app.app_settings  # noqa: F401
import app.approvals  # noqa: F401
import app.mcp_connector  # noqa: F401
import app.memory  # noqa: F401
import app.oauth  # noqa: F401
import app.proactive  # noqa: F401
import app.scheduler  # noqa: F401
import app.voice  # noqa: F401
from alembic import context
from app.models import Base

# Alembic Config object
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (SQL script generation)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode with a sync engine."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
