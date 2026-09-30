"""Tests for the Motes application factory and health endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def settings() -> Settings:
    """Test settings with safe defaults."""
    return Settings(debug=True)


@pytest.fixture
def client(settings: Settings) -> TestClient:
    """Test client with injected settings."""
    app = create_app(settings=settings)
    return TestClient(app)


@pytest.mark.unit
class TestHealthEndpoint:
    """Health endpoint tests."""

    def test_health_returns_200(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_status_ok(self, client: TestClient) -> None:
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "ok"

    def test_health_returns_app_name(self, client: TestClient) -> None:
        response = client.get("/health")
        data = response.json()
        assert data["app"] == "Motes"

    def test_health_returns_version(self, client: TestClient) -> None:
        response = client.get("/health")
        data = response.json()
        assert data["version"] == "0.1.0"


@pytest.mark.unit
class TestAppFactory:
    """Application factory tests."""

    def test_create_app_returns_fastapi(self, settings: Settings) -> None:
        app = create_app(settings=settings)
        assert app.title == "Motes"

    def test_create_app_default_settings(self) -> None:
        app = create_app()
        assert app.state.settings.app_name == "Motes"

    def test_create_app_custom_settings(self, settings: Settings) -> None:
        app = create_app(settings=settings)
        assert app.state.settings.debug is True


@pytest.mark.unit
class TestConfig:
    """Configuration tests."""

    def test_default_settings(self) -> None:
        s = Settings()
        assert s.app_name == "Motes"
        assert s.app_version == "0.1.0"
        assert s.debug is False
        assert s.llm_provider == "mock"

    def test_settings_override(self) -> None:
        s = Settings(debug=True, llm_provider="openai")
        assert s.debug is True
        assert s.llm_provider == "openai"
