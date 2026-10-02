"""Tests for incoming Slack + Telegram webhook channels.

TDD: these tests define the expected behaviour for receiving messages
from Slack and Telegram and responding in the same thread.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from unittest.mock import AsyncMock, patch

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
        secret_key="test-secret-for-webhooks-32ch!!",
    )
    application = create_app(settings=settings)
    with TestClient(application) as c:
        yield c


def _setup_user_and_agent(client: TestClient) -> tuple[str, str]:
    """Create a user + agent and return (token, agent_id).

    Creates provider/agent directly in DB since the provider
    create endpoint validates the connection.
    """
    resp = client.post("/api/auth/setup", json={
        "username": "admin",
        "password": "password123",
    })
    token = resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get user_id from a protected endpoint
    resp = client.get("/api/agents", headers=headers)
    assert resp.status_code == 200

    # We need to create provider+agent directly since the create endpoint
    # validates provider connectivity. Use a dedicated test-setup endpoint
    # approach: create via DB by posting to the internal test helper.
    # Actually, let's just use the add_provider function with mock.
    with patch("app.providers.test_provider_connection", new_callable=AsyncMock) as mock_test:
        mock_test.return_value = (True, "OK")
        resp = client.post("/api/providers", json={
            "name": "test-provider",
            "base_url": "https://api.test.com/v1",
            "api_key": "sk-test-key",
            "model": "gpt-4",
        }, headers=headers)
        assert resp.status_code == 201, f"Provider creation failed: {resp.json()}"
        provider_id = resp.json()["id"]

    # Create agent
    resp = client.post("/api/agents", json={
        "name": "Test Agent",
        "provider_id": provider_id,
        "system_prompt": "You are helpful.",
    }, headers=headers)
    assert resp.status_code in (200, 201), f"Agent creation failed: {resp.json()}"
    agent_id = resp.json()["id"]

    return token, agent_id


def _slack_signature(body: bytes, secret: str = "test-slack-signing-secret", ts: str | None = None) -> tuple[str, str]:
    """Generate a valid Slack request signature."""
    timestamp = ts or str(int(time.time()))
    sig_basestring = f"v0:{timestamp}:{body.decode()}"
    signature = "v0=" + hmac.new(
        secret.encode(), sig_basestring.encode(), hashlib.sha256
    ).hexdigest()
    return timestamp, signature


# ── Slack Tests ──────────────────────────────────────────


@pytest.mark.unit
class TestSlackWebhook:
    """Slack incoming webhook tests."""

    def test_slack_webhook_verification(self, client: TestClient) -> None:
        """Slack sends a url_verification challenge; we must echo it back."""
        payload = {
            "type": "url_verification",
            "challenge": "test-challenge-token-abc123",
            "token": "deprecated-verification-token",
        }
        body = json.dumps(payload).encode()
        ts, sig = _slack_signature(body)
        with patch.dict("os.environ", {"SLACK_SIGNING_SECRET": "test-slack-signing-secret"}):
            resp = client.post(
                "/api/webhooks/slack",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Slack-Request-Timestamp": ts,
                    "X-Slack-Signature": sig,
                },
            )
        assert resp.status_code == 200
        assert resp.json()["challenge"] == "test-challenge-token-abc123"

    def test_slack_message_received(self, client: TestClient) -> None:
        """A message event from Slack triggers agent processing."""
        token, agent_id = _setup_user_and_agent(client)

        # Configure channel mapping
        with patch.dict("os.environ", {
            "SLACK_SIGNING_SECRET": "test-slack-signing-secret",
            "SLACK_BOT_TOKEN": "xoxb-test-token",
        }):
            # Store channel-to-agent mapping
            client.post("/api/webhooks/slack/config", json={
                "channel_id": "C12345",
                "agent_id": agent_id,
            }, headers={"Authorization": f"Bearer {token}"})

            payload = {
                "type": "event_callback",
                "event": {
                    "type": "message",
                    "channel": "C12345",
                    "user": "U99999",
                    "text": "Hello Motes from Slack!",
                    "ts": "1234567890.123456",
                },
            }
            body = json.dumps(payload).encode()
            ts, sig = _slack_signature(body)

            with patch("app.routes.webhooks._run_agent_for_channel", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = "Hello from Motes!"
                resp = client.post(
                    "/api/webhooks/slack",
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-Slack-Request-Timestamp": ts,
                        "X-Slack-Signature": sig,
                    },
                )

            assert resp.status_code == 200
            assert resp.json()["status"] == "ok"

    def test_slack_response_sent(self, client: TestClient) -> None:
        """Agent response is posted back to the Slack thread."""
        token, agent_id = _setup_user_and_agent(client)

        with patch.dict("os.environ", {
            "SLACK_SIGNING_SECRET": "test-slack-signing-secret",
            "SLACK_BOT_TOKEN": "xoxb-test-token",
        }):
            client.post("/api/webhooks/slack/config", json={
                "channel_id": "C12345",
                "agent_id": agent_id,
            }, headers={"Authorization": f"Bearer {token}"})

            payload = {
                "type": "event_callback",
                "event": {
                    "type": "message",
                    "channel": "C12345",
                    "user": "U99999",
                    "text": "What's the weather?",
                    "ts": "1234567890.123456",
                },
            }
            body = json.dumps(payload).encode()
            ts, sig = _slack_signature(body)

            with (
                patch("app.routes.webhooks._run_agent_for_channel", new_callable=AsyncMock) as mock_run,
                patch("app.routes.webhooks._send_slack_reply", new_callable=AsyncMock) as mock_send,
            ):
                mock_run.return_value = "It's sunny today!"
                resp = client.post(
                    "/api/webhooks/slack",
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-Slack-Request-Timestamp": ts,
                        "X-Slack-Signature": sig,
                    },
                )

            assert resp.status_code == 200
            # Verify the reply function was called with correct args
            mock_send.assert_called_once_with(
                channel="C12345",
                text="It's sunny today!",
                thread_ts="1234567890.123456",
            )

    def test_slack_invalid_signature_rejected(self, client: TestClient) -> None:
        """Requests with invalid Slack signatures are rejected."""
        payload = {"type": "url_verification", "challenge": "test"}
        body = json.dumps(payload).encode()
        with patch.dict("os.environ", {"SLACK_SIGNING_SECRET": "test-slack-signing-secret"}):
            resp = client.post(
                "/api/webhooks/slack",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Slack-Request-Timestamp": str(int(time.time())),
                    "X-Slack-Signature": "v0=invalidsignature",
                },
            )
        assert resp.status_code == 403

    def test_slack_bot_message_ignored(self, client: TestClient) -> None:
        """Bot messages (including our own) should be ignored to prevent loops."""
        payload = {
            "type": "event_callback",
            "event": {
                "type": "message",
                "subtype": "bot_message",
                "channel": "C12345",
                "text": "I'm a bot message",
                "ts": "1234567890.123456",
            },
        }
        body = json.dumps(payload).encode()
        ts, sig = _slack_signature(body)
        with patch.dict("os.environ", {"SLACK_SIGNING_SECRET": "test-slack-signing-secret"}):
            resp = client.post(
                "/api/webhooks/slack",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Slack-Request-Timestamp": ts,
                    "X-Slack-Signature": sig,
                },
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"


# ── Telegram Tests ───────────────────────────────────────


@pytest.mark.unit
class TestTelegramWebhook:
    """Telegram incoming webhook tests."""

    def test_telegram_webhook_message(self, client: TestClient) -> None:
        """A Telegram update with a text message is processed."""
        token, agent_id = _setup_user_and_agent(client)

        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "123456:ABC-test-token"}):
            # Configure chat-to-agent mapping
            client.post("/api/webhooks/telegram/config", json={
                "chat_id": "98765",
                "agent_id": agent_id,
            }, headers={"Authorization": f"Bearer {token}"})

            update = {
                "update_id": 100,
                "message": {
                    "message_id": 1,
                    "from": {"id": 42, "first_name": "Luis", "is_bot": False},
                    "chat": {"id": 98765, "type": "private"},
                    "date": 1700000000,
                    "text": "Hello Motes from Telegram!",
                },
            }

            with patch("app.routes.webhooks._run_agent_for_channel", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = "Hi from Motes!"
                resp = client.post(
                    "/api/webhooks/telegram",
                    json=update,
                    headers={"X-Telegram-Bot-Api-Secret-Token": "123456:ABC-test-token"},
                )

            assert resp.status_code == 200
            assert resp.json()["status"] == "ok"

    def test_telegram_response_sent(self, client: TestClient) -> None:
        """Agent response is sent back via Telegram sendMessage API."""
        token, agent_id = _setup_user_and_agent(client)

        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "123456:ABC-test-token"}):
            client.post("/api/webhooks/telegram/config", json={
                "chat_id": "98765",
                "agent_id": agent_id,
            }, headers={"Authorization": f"Bearer {token}"})

            update = {
                "update_id": 101,
                "message": {
                    "message_id": 2,
                    "from": {"id": 42, "first_name": "Luis", "is_bot": False},
                    "chat": {"id": 98765, "type": "private"},
                    "date": 1700000001,
                    "text": "What time is it?",
                },
            }

            with (
                patch("app.routes.webhooks._run_agent_for_channel", new_callable=AsyncMock) as mock_run,
                patch("app.routes.webhooks._send_telegram_reply", new_callable=AsyncMock) as mock_send,
            ):
                mock_run.return_value = "It's 3pm!"
                resp = client.post(
                    "/api/webhooks/telegram",
                    json=update,
                    headers={"X-Telegram-Bot-Api-Secret-Token": "123456:ABC-test-token"},
                )

            assert resp.status_code == 200
            mock_send.assert_called_once_with(
                chat_id=98765,
                text="It's 3pm!",
                reply_to_message_id=2,
            )

    def test_telegram_bot_message_ignored(self, client: TestClient) -> None:
        """Messages from bots should be ignored."""
        update = {
            "update_id": 102,
            "message": {
                "message_id": 3,
                "from": {"id": 99, "first_name": "Bot", "is_bot": True},
                "chat": {"id": 98765, "type": "private"},
                "date": 1700000002,
                "text": "I'm a bot",
            },
        }

        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "123456:ABC-test-token"}):
            resp = client.post(
                "/api/webhooks/telegram",
                json=update,
                headers={"X-Telegram-Bot-Api-Secret-Token": "123456:ABC-test-token"},
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    def test_telegram_no_text_ignored(self, client: TestClient) -> None:
        """Updates without text (photos, stickers, etc.) are ignored."""
        update = {
            "update_id": 103,
            "message": {
                "message_id": 4,
                "from": {"id": 42, "first_name": "Luis", "is_bot": False},
                "chat": {"id": 98765, "type": "private"},
                "date": 1700000003,
                "sticker": {"file_id": "sticker123"},
            },
        }

        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "123456:ABC-test-token"}):
            resp = client.post(
                "/api/webhooks/telegram",
                json=update,
                headers={"X-Telegram-Bot-Api-Secret-Token": "123456:ABC-test-token"},
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"


# ── Thread persistence tests ────────────────────────────


@pytest.mark.unit
class TestChannelThreadPersistence:
    """Messages from channels should be saved to the unified thread."""

    def test_channel_message_saved_to_thread(self, client: TestClient) -> None:
        """Incoming Slack message is saved with message_type='slack'."""
        token, agent_id = _setup_user_and_agent(client)
        headers = {"Authorization": f"Bearer {token}"}

        with patch.dict("os.environ", {
            "SLACK_SIGNING_SECRET": "test-slack-signing-secret",
            "SLACK_BOT_TOKEN": "xoxb-test-token",
        }):
            client.post("/api/webhooks/slack/config", json={
                "channel_id": "C12345",
                "agent_id": agent_id,
            }, headers=headers)

            payload = {
                "type": "event_callback",
                "event": {
                    "type": "message",
                    "channel": "C12345",
                    "user": "U99999",
                    "text": "Save this to thread",
                    "ts": "1234567890.999",
                },
            }
            body = json.dumps(payload).encode()
            ts, sig = _slack_signature(body)

            with patch("app.routes.webhooks._run_agent_for_channel", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = "Saved!"
                client.post(
                    "/api/webhooks/slack",
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-Slack-Request-Timestamp": ts,
                        "X-Slack-Signature": sig,
                    },
                )

        # Check thread has the message
        resp = client.get(f"/api/agents/{agent_id}/thread", headers=headers)
        assert resp.status_code == 200
        messages = resp.json()["messages"]
        slack_msgs = [m for m in messages if m["message_type"] == "slack"]
        assert len(slack_msgs) >= 1
        assert any("Save this to thread" in m["content"] for m in slack_msgs)

    def test_channel_response_saved_to_thread(self, client: TestClient) -> None:
        """Agent response to Telegram is saved with message_type='telegram'."""
        token, agent_id = _setup_user_and_agent(client)
        headers = {"Authorization": f"Bearer {token}"}

        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "123456:ABC-test-token"}):
            client.post("/api/webhooks/telegram/config", json={
                "chat_id": "98765",
                "agent_id": agent_id,
            }, headers=headers)

            update = {
                "update_id": 200,
                "message": {
                    "message_id": 10,
                    "from": {"id": 42, "first_name": "Luis", "is_bot": False},
                    "chat": {"id": 98765, "type": "private"},
                    "date": 1700000010,
                    "text": "Telegram thread test",
                },
            }

            with (
                patch("app.routes.webhooks._run_agent_for_channel", new_callable=AsyncMock) as mock_run,
                patch("app.routes.webhooks._send_telegram_reply", new_callable=AsyncMock),
            ):
                mock_run.return_value = "Agent reply via Telegram"
                client.post(
                    "/api/webhooks/telegram",
                    json=update,
                    headers={"X-Telegram-Bot-Api-Secret-Token": "123456:ABC-test-token"},
                )

        # Check thread has both user and assistant messages
        resp = client.get(f"/api/agents/{agent_id}/thread", headers=headers)
        assert resp.status_code == 200
        messages = resp.json()["messages"]
        telegram_msgs = [m for m in messages if m["message_type"] == "telegram"]
        assert len(telegram_msgs) >= 2  # user + assistant
        roles = [m["role"] for m in telegram_msgs]
        assert "user" in roles
        assert "assistant" in roles
