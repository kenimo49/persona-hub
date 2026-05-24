"""Smoke test for rate limit wiring.

Full per-key + per-IP limit exercises depend on slowapi's well-tested internals.
Here we just confirm that the limiter is wired and that ``_composite_key`` runs
when rate-limiting is enabled.
"""

from fastapi import Request
from fastapi.testclient import TestClient

from app.main import app
from app.rate_limit import _composite_key


def _build_request(headers: list[tuple[bytes, bytes]]) -> Request:
    scope: dict[str, object] = {
        "type": "http",
        "headers": headers,
        "client": ("127.0.0.1", 1234),
    }
    return Request(scope)  # type: ignore[arg-type]


def test_composite_key_uses_api_key_when_present() -> None:
    req = _build_request([(b"x-api-key", b"ph_abcdefghijklm")])
    key = _composite_key(req)
    assert key.startswith("key:")
    assert len(key) == len("key:") + 16  # 16 hex chars from sha256 prefix


def test_composite_key_distinguishes_different_keys() -> None:
    """Two keys that share a lookup prefix must land in different rate-limit buckets."""
    a = _build_request([(b"x-api-key", b"ph_abcdefgh_TAIL_A")])
    b = _build_request([(b"x-api-key", b"ph_abcdefgh_TAIL_B")])
    assert _composite_key(a) != _composite_key(b)


def test_composite_key_falls_back_to_ip() -> None:
    req = _build_request([])
    key = _composite_key(req)
    assert key.startswith("ip:")


def test_limiter_attached_to_app() -> None:
    assert app.state.limiter is not None


def test_rate_limit_path_when_enabled(client: TestClient) -> None:
    """When the limit is high (default 100/min) requests succeed normally.

    We toggle ``enabled`` to True temporarily to exercise the middleware
    code path even though the suite runs with rate-limiting off by default.
    """
    app.state.limiter.enabled = True
    try:
        for _ in range(3):
            res = client.get("/health")
            assert res.status_code == 200
    finally:
        app.state.limiter.enabled = False
