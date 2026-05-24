"""Tests for ``POST /personas`` and ``GET /personas/:id``."""

from typing import Any

from fastapi.testclient import TestClient

from .conftest import fragrance_payload


def test_create_persona_returns_id(client: TestClient, kaoriq_key: str) -> None:
    res = client.post("/personas", json=fragrance_payload(), headers={"X-API-Key": kaoriq_key})
    assert res.status_code == 201
    body: dict[str, Any] = res.json()
    assert len(body["persona_id"]) == 26


def test_create_persona_requires_api_key(client: TestClient) -> None:
    res = client.post("/personas", json=fragrance_payload())
    assert res.status_code == 401
    assert "Missing X-API-Key" in res.json()["detail"]


def test_create_persona_rejects_invalid_key(client: TestClient) -> None:
    res = client.post(
        "/personas",
        json=fragrance_payload(),
        headers={"X-API-Key": "ph_invalidkey1234567890"},
    )
    assert res.status_code == 401


def test_create_persona_rejects_disabled_key(client: TestClient, disabled_key: str) -> None:
    res = client.post(
        "/personas", json=fragrance_payload(source="disabled-key"),
        headers={"X-API-Key": disabled_key},
    )
    assert res.status_code == 401


def test_create_persona_rejects_short_key(client: TestClient) -> None:
    res = client.post(
        "/personas", json=fragrance_payload(), headers={"X-API-Key": "ph_x"}
    )
    assert res.status_code == 401
    assert "Invalid API key format" in res.json()["detail"]


def test_create_persona_rejects_correct_prefix_wrong_tail(
    client: TestClient, kaoriq_key: str
) -> None:
    """A key with a real prefix but a corrupted tail must fail hash verification."""
    forged = kaoriq_key[:11] + "X" * (len(kaoriq_key) - 11)
    assert forged != kaoriq_key
    res = client.post(
        "/personas", json=fragrance_payload(), headers={"X-API-Key": forged}
    )
    assert res.status_code == 401


def test_create_persona_validates_body(client: TestClient, kaoriq_key: str) -> None:
    res = client.post(
        "/personas",
        json={"source": "kaoriq"},
        headers={"X-API-Key": kaoriq_key},
    )
    assert res.status_code == 422


def test_create_persona_rejects_source_spoof(
    client: TestClient, kaoriq_key: str
) -> None:
    """The client cannot attribute writes to a different source service."""
    payload = fragrance_payload(source="mypcrig")  # mismatched
    res = client.post("/personas", json=payload, headers={"X-API-Key": kaoriq_key})
    assert res.status_code == 400
    assert "source must match" in res.json()["detail"]


def test_get_persona_returns_signals(client: TestClient, kaoriq_key: str) -> None:
    create = client.post(
        "/personas", json=fragrance_payload(), headers={"X-API-Key": kaoriq_key}
    )
    persona_id = create.json()["persona_id"]

    res = client.get(f"/personas/{persona_id}", headers={"X-API-Key": kaoriq_key})
    assert res.status_code == 200
    body = res.json()
    assert body["persona_id"] == persona_id
    assert len(body["signals"]) == 1
    assert body["signals"][0]["profile_id"] == "fragrance.v1"
    assert body["aggregate"] is None


def test_get_persona_404_when_missing(client: TestClient, kaoriq_key: str) -> None:
    res = client.get(
        "/personas/00000000000000000000000000", headers={"X-API-Key": kaoriq_key}
    )
    assert res.status_code == 404


def test_get_persona_403_for_other_key(
    client: TestClient, kaoriq_key: str, mypcrig_key: str
) -> None:
    create = client.post(
        "/personas", json=fragrance_payload(), headers={"X-API-Key": kaoriq_key}
    )
    persona_id = create.json()["persona_id"]
    res = client.get(f"/personas/{persona_id}", headers={"X-API-Key": mypcrig_key})
    assert res.status_code == 403


def test_profile_whitelist_enforced_on_create(
    client: TestClient, fragrance_only_key: str
) -> None:
    bad = fragrance_payload(source="fragrance-only")
    bad["profile_id"] = "pc.v1"
    res = client.post("/personas", json=bad, headers={"X-API-Key": fragrance_only_key})
    assert res.status_code == 403
    assert "not allowed to write profile_id" in res.json()["detail"]


def test_profile_whitelist_allows_matching(
    client: TestClient, fragrance_only_key: str
) -> None:
    res = client.post(
        "/personas",
        json=fragrance_payload(source="fragrance-only"),
        headers={"X-API-Key": fragrance_only_key},
    )
    assert res.status_code == 201
