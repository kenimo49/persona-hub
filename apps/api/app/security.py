"""Cryptographic helpers: API key hashing + JWT handoff token encoding."""

import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from typing import Any, TypedDict, cast

import jwt

from app.config import get_settings

JWT_ISSUER = "persona-hub"


class HandoffClaims(TypedDict):
    """Validated handoff token claims."""

    iss: str
    jti: str
    sub: str  # persona_id being shared
    iss_key: str  # id of the issuing source API key
    iat: int
    exp: int


def hash_api_key(key: str) -> str:
    """Return the SHA-256 hex digest of an API key.

    The key itself carries ~192 bits of entropy (``secrets.token_urlsafe(24)``),
    so a single SHA-256 pass is sufficient and ``hmac.compare_digest`` resists
    timing attacks. We deliberately do not use argon2/bcrypt here — they exist
    to slow down attacks on low-entropy human passwords, which API keys are not.
    """
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def verify_api_key(key: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_api_key(key), stored_hash)


def encode_handoff_token(
    persona_id: str, issuing_key_id: str, jti: str
) -> tuple[str, datetime]:
    """Sign a handoff token. Returns ``(token, expires_at)``."""
    settings = get_settings()
    now = datetime.now(UTC)
    exp = now + timedelta(seconds=settings.handoff_token_ttl_seconds)
    payload: dict[str, Any] = {
        "iss": JWT_ISSUER,
        "jti": jti,
        "sub": persona_id,
        "iss_key": issuing_key_id,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, exp


def decode_handoff_token(token: str) -> HandoffClaims:
    """Verify and return claims. Raises ``jwt.PyJWTError`` on failure."""
    settings = get_settings()
    decoded = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        issuer=JWT_ISSUER,
        options={"require": ["exp", "iat", "iss", "jti", "sub"]},
    )
    if "iss_key" not in decoded:
        raise jwt.InvalidTokenError("Missing iss_key claim")
    return cast(HandoffClaims, decoded)
