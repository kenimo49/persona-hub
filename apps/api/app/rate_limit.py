"""slowapi rate limiter.

Uses a composite key: per-API-key when an ``X-API-Key`` header is present,
otherwise per source IP. A single conservative limit applies to both buckets
to keep the MVP simple; per-key + per-IP separate limits can be layered later
via stacked ``@limiter.limit`` decorators on individual endpoints.
"""

import hashlib

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings


def _composite_key(request: Request) -> str:
    """Bucket requests by full API-key hash, falling back to client IP.

    We hash the *entire* submitted header value (not the lookup prefix) so a
    malicious anonymous request cannot exhaust a legitimate tenant's quota by
    sending a header that shares the tenant's lookup prefix. Hashing also
    keeps the raw key out of slowapi's in-memory state and any error logs.
    """
    api_key = request.headers.get("X-API-Key")
    if api_key:
        digest = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16]
        return f"key:{digest}"
    return f"ip:{get_remote_address(request)}"


_limiter: Limiter | None = None


def get_limiter() -> Limiter:
    global _limiter
    if _limiter is None:
        settings = get_settings()
        _limiter = Limiter(
            key_func=_composite_key,
            default_limits=[settings.rate_limit_default],
            enabled=settings.enable_rate_limit,
        )
    return _limiter
