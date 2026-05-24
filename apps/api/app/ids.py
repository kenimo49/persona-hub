"""ID and API key generation helpers."""

import secrets

from ulid import ULID

API_KEY_PREFIX = "ph_"
API_KEY_LOOKUP_LEN = 11  # ``ph_`` + 8 random chars; used as the indexed lookup column


def new_ulid() -> str:
    """Return a Crockford base32 ULID string (26 chars)."""
    return str(ULID())


def new_api_key() -> str:
    """Generate a new opaque API key.

    Format: ``ph_<32 url-safe random chars>`` (~192 bits of entropy in the random part).
    The literal value is shown to the caller exactly once and never stored; only a
    SHA-256 hash and an indexed lookup prefix persist.
    """
    return API_KEY_PREFIX + secrets.token_urlsafe(24)


def api_key_lookup_prefix(key: str) -> str:
    """Extract the indexable lookup prefix from a raw API key."""
    return key[:API_KEY_LOOKUP_LEN]
