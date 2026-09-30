"""Tests for persistent agent memory."""

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    settings = Settings(
        debug=True,
        database_url="sqlite+aiosqlite:///:memory:",
        secret_key="test-secret-for-memory-32chars!!",
    )
    application = create_app(settings=settings)
    with TestClient(application) as c:
        yield c


def _setup_and_get_token(client: TestClient) -> str:
    """Create user and return JWT token."""
    client.post("/api/auth/setup", json={
        "username": "admin",
        "password": "password123",
    })
    resp = client.post("/api/auth/login", json={
        "username": "admin",
        "password": "password123",
    })
    return resp.json()["token"]


def _create_agent(client: TestClient, token: str, provider_id: str) -> str:
    """Create an agent and return its ID."""
    resp = client.post(
        "/api/agents",
        json={
            "name": "Test Agent",
            "provider_id": provider_id,
            "system_prompt": "You are helpful.",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()["id"]


@pytest.mark.unit
class TestMemoryRoutes:
    """Memory CRUD tests."""

    def _setup_agent(self, client: TestClient):
        """Setup user + mock provider + agent, return (token, agent_id)."""
        token = _setup_and_get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        # We need a provider first — create one directly via DB
        # For simplicity, let's use the test provider endpoint
        # But it requires a real connection... let's create via the model
        # Instead, let's patch the provider test
        from unittest.mock import AsyncMock, MagicMock, patch
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("app.providers.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            resp = client.post(
                "/api/providers",
                json={
                    "name": "Test Provider",
                    "base_url": "http://fake.local/v1",
                    "api_key": "fake-key",
                    "model": "gpt-test",
                },
                headers=headers,
            )
        provider_id = resp.json()["id"]
        agent_id = _create_agent(client, token, provider_id)
        return token, agent_id

    def test_create_memory(self, client: TestClient) -> None:
        token, agent_id = self._setup_agent(client)
        resp = client.post(
            f"/api/agents/{agent_id}/memories",
            json={"content": "User prefers dark mode", "category": "preferences"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["content"] == "User prefers dark mode"
        assert data["category"] == "preferences"

    def test_list_memories(self, client: TestClient) -> None:
        token, agent_id = self._setup_agent(client)
        headers = {"Authorization": f"Bearer {token}"}
        client.post(
            f"/api/agents/{agent_id}/memories",
            json={"content": "Fact 1", "category": "facts"},
            headers=headers,
        )
        client.post(
            f"/api/agents/{agent_id}/memories",
            json={"content": "Fact 2", "category": "facts"},
            headers=headers,
        )
        resp = client.get(
            f"/api/agents/{agent_id}/memories",
            headers=headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_list_memories_by_category(self, client: TestClient) -> None:
        token, agent_id = self._setup_agent(client)
        headers = {"Authorization": f"Bearer {token}"}
        client.post(
            f"/api/agents/{agent_id}/memories",
            json={"content": "Pref 1", "category": "preferences"},
            headers=headers,
        )
        client.post(
            f"/api/agents/{agent_id}/memories",
            json={"content": "Fact 1", "category": "facts"},
            headers=headers,
        )
        resp = client.get(
            f"/api/agents/{agent_id}/memories?category=preferences",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["category"] == "preferences"

    def test_update_memory(self, client: TestClient) -> None:
        token, agent_id = self._setup_agent(client)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post(
            f"/api/agents/{agent_id}/memories",
            json={"content": "Old fact"},
            headers=headers,
        )
        memory_id = resp.json()["id"]
        resp = client.put(
            f"/api/agents/{agent_id}/memories/{memory_id}",
            json={"content": "Updated fact"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["content"] == "Updated fact"

    def test_delete_memory(self, client: TestClient) -> None:
        token, agent_id = self._setup_agent(client)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post(
            f"/api/agents/{agent_id}/memories",
            json={"content": "Temp note"},
            headers=headers,
        )
        memory_id = resp.json()["id"]
        resp = client.delete(
            f"/api/agents/{agent_id}/memories/{memory_id}",
            headers=headers,
        )
        assert resp.status_code == 204
        # Verify gone
        resp = client.get(
            f"/api/agents/{agent_id}/memories",
            headers=headers,
        )
        assert len(resp.json()) == 0

    def test_search_memories(self, client: TestClient) -> None:
        token, agent_id = self._setup_agent(client)
        headers = {"Authorization": f"Bearer {token}"}
        client.post(
            f"/api/agents/{agent_id}/memories",
            json={"content": "User likes pizza"},
            headers=headers,
        )
        client.post(
            f"/api/agents/{agent_id}/memories",
            json={"content": "Meeting at 3pm"},
            headers=headers,
        )
        resp = client.get(
            f"/api/agents/{agent_id}/memories/search?q=pizza",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert "pizza" in data[0]["content"]
