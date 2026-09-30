"""Tests for authentication: setup, login, JWT."""

import pytest

from app.auth import (
    authenticate,
    create_jwt,
    decode_jwt,
    hash_password,
    is_setup_complete,
    setup_first_user,
    verify_password,
)


@pytest.mark.unit
class TestPasswordHashing:
    """Password hashing tests."""

    def test_hash_and_verify(self) -> None:
        hashed = hash_password("mypassword123")
        assert verify_password("mypassword123", hashed)

    def test_wrong_password_fails(self) -> None:
        hashed = hash_password("mypassword123")
        assert not verify_password("wrongpassword", hashed)

    def test_hash_format(self) -> None:
        hashed = hash_password("test")
        assert hashed.startswith("scrypt$")
        parts = hashed.split("$")
        assert len(parts) == 3

    def test_different_salts(self) -> None:
        h1 = hash_password("same")
        h2 = hash_password("same")
        # Different salts produce different hashes
        assert h1 != h2
        # But both verify correctly
        assert verify_password("same", h1)
        assert verify_password("same", h2)


@pytest.mark.unit
class TestJWT:
    """JWT token tests."""

    def test_create_and_decode(self) -> None:
        token = create_jwt("user-123", "secret")
        payload = decode_jwt(token, "secret")
        assert payload is not None
        assert payload["sub"] == "user-123"

    def test_wrong_secret_fails(self) -> None:
        token = create_jwt("user-123", "secret")
        payload = decode_jwt(token, "wrong-secret")
        assert payload is None

    def test_invalid_token_fails(self) -> None:
        payload = decode_jwt("garbage.token.here", "secret")
        assert payload is None


@pytest.mark.unit
class TestSetup:
    """First-user setup tests."""

    @pytest.mark.asyncio
    async def test_no_users_means_setup_incomplete(self, session) -> None:
        assert not await is_setup_complete(session)

    @pytest.mark.asyncio
    async def test_setup_first_user(self, session) -> None:
        user = await setup_first_user(session, "admin", "password123")
        assert user.username == "admin"
        assert user.is_admin is True
        assert await is_setup_complete(session)

    @pytest.mark.asyncio
    async def test_setup_twice_fails(self, session) -> None:
        await setup_first_user(session, "admin", "password123")
        with pytest.raises(ValueError, match="Setup already complete"):
            await setup_first_user(session, "admin2", "password456")


@pytest.mark.unit
class TestAuthenticate:
    """Login authentication tests."""

    @pytest.mark.asyncio
    async def test_valid_login(self, session) -> None:
        await setup_first_user(session, "admin", "password123")
        user = await authenticate(session, "admin", "password123")
        assert user is not None
        assert user.username == "admin"

    @pytest.mark.asyncio
    async def test_wrong_password(self, session) -> None:
        await setup_first_user(session, "admin", "password123")
        user = await authenticate(session, "admin", "wrongpass")
        assert user is None

    @pytest.mark.asyncio
    async def test_nonexistent_user(self, session) -> None:
        user = await authenticate(session, "nobody", "password")
        assert user is None
