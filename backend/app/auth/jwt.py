"""
JWT creation and verification for access tokens.

Uses the app secret key and algorithm from config. Tokens include
sub (subject, typically user id), exp (expiry), and iat (issued at).
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from app.config import settings


def create_access_token(sub: str | int, extra_claims: dict[str, Any] | None = None) -> str:
    """
    Build a signed JWT access token.

    Args:
        sub: Subject (e.g. user id) stored as string in the token.
        extra_claims: Optional additional key-value pairs to include in the payload.

    Returns:
        Encoded JWT string.
    """
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(sub),
        "exp": expire,
        "iat": now,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """
    Verify and decode a JWT access token.

    Args:
        token: The raw JWT string from the Authorization header.

    Returns:
        The decoded payload dict if valid and not expired; None otherwise.
    """
    try:
        return jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
    except JWTError:
        return None
