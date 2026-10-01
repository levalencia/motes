"""Authentication: single-user setup, scrypt passwords, JWT tokens."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import jwt
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User

logger = structlog.get_logger()

_JWT_ALGORITHM = "HS256"
_JWT_EXPIRY = timedelta(hours=24)


def hash_password(password: str, salt: bytes | None = None) -> str:
    """Hash with scrypt + random salt."""
    salt = salt or secrets.token_bytes(16)
    import base64

    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    salt_text = base64.urlsafe_b64encode(salt).decode()
    digest_text = base64.urlsafe_b64encode(digest).decode()
    return f"scrypt${salt_text}${digest_text}"


def verify_password(password: str, encoded: str) -> bool:
    """Verify a scrypt-hashed password."""
    import base64

    try:
        algorithm, salt_text, digest_text = encoded.split("$", 2)
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_text)
        expected = base64.urlsafe_b64decode(digest_text)
        actual = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_jwt(user_id: str, secret: str, username: str = "") -> str:
    """Create a signed JWT for the given user."""
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "username": username,
        "iat": now,
        "exp": now + _JWT_EXPIRY,
    }
    return jwt.encode(payload, secret, algorithm=_JWT_ALGORITHM)


def decode_jwt(token: str, secret: str) -> dict | None:
    """Decode and validate a JWT. Returns payload or None."""
    try:
        return jwt.decode(token, secret, algorithms=[_JWT_ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


async def is_setup_complete(session: AsyncSession) -> bool:
    """Check if any user exists (setup is done)."""
    result = await session.execute(select(User).limit(1))
    return result.scalar_one_or_none() is not None


async def setup_first_user(
    session: AsyncSession, username: str, password: str
) -> User:
    """Create the first admin user. Raises if setup already done."""
    if await is_setup_complete(session):
        raise ValueError("Setup already complete")
    user = User(
        username=username,
        password_hash=hash_password(password),
        is_admin=True,
        is_setup_complete=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def authenticate(
    session: AsyncSession, username: str, password: str
) -> User | None:
    """Authenticate by username + password. Returns User or None."""
    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user and verify_password(password, user.password_hash):
        return user
    return None
