"""Tests for API routes: auth, providers, agents."""

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    """Test client with in-memory SQLite and lifespan context."""
    settings = Settings(
        debug=True,
        database_url="sqlite+aiosqlite:///:memory:",
        secret_key="test-secret-for-routes-32chars!!",
    )
    application = create_app(settings=settings)
    with TestClient(application) as c:
        yield c


@pytest.mark.unit
class TestAuthRoutes:
    """Auth endpoint tests."""

    def test_setup_status_initially_false(self, client: TestClient) -> None:
        resp = client.get("/api/auth/setup-status")
        assert resp.status_code == 200
        assert resp.json()["is_setup_complete"] is False

    def test_setup_creates_user(self, client: TestClient) -> None:
        resp = client.post(
            "/api/auth/setup",
            json={
                "username": "admin",
                "password": "password123",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["username"] == "admin"

    def test_setup_twice_fails(self, client: TestClient) -> None:
        client.post(
            "/api/auth/setup",
            json={
                "username": "admin",
                "password": "password123",
            },
        )
        resp = client.post(
            "/api/auth/setup",
            json={
                "username": "admin2",
                "password": "password456",
            },
        )
        assert resp.status_code == 409

    def test_login_after_setup(self, client: TestClient) -> None:
        client.post(
            "/api/auth/setup",
            json={
                "username": "admin",
                "password": "password123",
            },
        )
        resp = client.post(
            "/api/auth/login",
            json={
                "username": "admin",
                "password": "password123",
            },
        )
        assert resp.status_code == 200
        assert "token" in resp.json()

    def test_login_wrong_password(self, client: TestClient) -> None:
        client.post(
            "/api/auth/setup",
            json={
                "username": "admin",
                "password": "password123",
            },
        )
        resp = client.post(
            "/api/auth/login",
            json={
                "username": "admin",
                "password": "wrongpass",
            },
        )
        assert resp.status_code == 401

    def test_setup_status_after_setup(self, client: TestClient) -> None:
        client.post(
            "/api/auth/setup",
            json={
                "username": "admin",
                "password": "password123",
            },
        )
        resp = client.get("/api/auth/setup-status")
        assert resp.json()["is_setup_complete"] is True


@pytest.mark.unit
class TestProtectedRoutes:
    """Test that protected routes require authentication."""

    def test_providers_requires_auth(self, client: TestClient) -> None:
        resp = client.get("/api/providers")
        assert resp.status_code in (401, 403)

    def test_agents_requires_auth(self, client: TestClient) -> None:
        resp = client.get("/api/agents")
        assert resp.status_code in (401, 403)

    def _get_token(self, client: TestClient) -> str:
        client.post(
            "/api/auth/setup",
            json={
                "username": "admin",
                "password": "password123",
            },
        )
        resp = client.post(
            "/api/auth/login",
            json={
                "username": "admin",
                "password": "password123",
            },
        )
        return resp.json()["token"]

    def test_providers_with_auth(self, client: TestClient) -> None:
        token = self._get_token(client)
        resp = client.get(
            "/api/providers",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_agents_with_auth(self, client: TestClient) -> None:
        token = self._get_token(client)
        resp = client.get(
            "/api/agents",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json() == []
