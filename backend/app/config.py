"""Application configuration via Pydantic Settings."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Motes configuration. All values can be overridden via environment variables."""

    # App
    app_name: str = "Motes"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://motes:motes_dev@localhost:5433/motes",
        description="Async PostgreSQL connection string",
    )

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6380/0",
        description="Redis connection URL",
    )

    # LLM Provider (vendor-neutral)
    llm_provider: str = "mock"  # mock | openai | anthropic | ollama
    llm_model: str = "mock-model"
    llm_api_key: str = ""
    llm_base_url: str = ""

    # OpenTelemetry
    otel_enabled: bool = False
    otel_service_name: str = "motes"
    otel_exporter_endpoint: str = "http://localhost:4319"

    # Security
    secret_key: str = ""  # REQUIRED: set MOTES_SECRET_KEY env var

    # Azure OpenAI Realtime (voice calls)
    realtime_url: str = ""
    realtime_key: str = ""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {"env_prefix": "MOTES_", "env_file": ".env", "extra": "ignore"}


def get_settings() -> Settings:
    """Return application settings (cached per process)."""
    return Settings()
