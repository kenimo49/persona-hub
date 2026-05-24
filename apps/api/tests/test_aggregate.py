"""Tests for ``GET /personas/:id/aggregate``."""

from fastapi.testclient import TestClient

from .conftest import fragrance_payload


def test_aggregate_returns_placeholder(client: TestClient, kaoriq_key: str) -> None:
    persona_id = client.post(
        "/personas", json=fragrance_payload(), headers={"X-API-Key": kaoriq_key}
    ).json()["persona_id"]

    res = client.get(
        f"/personas/{persona_id}/aggregate",
        headers={"X-API-Key": kaoriq_key},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["persona_id"] == persona_id
    assert body["placeholder"] is True
    assert body["big_five_estimate"] is None
    assert body["summary"] is None


def test_aggregate_404_when_persona_missing(client: TestClient, kaoriq_key: str) -> None:
    res = client.get(
        "/personas/00000000000000000000000000/aggregate",
        headers={"X-API-Key": kaoriq_key},
    )
    assert res.status_code == 404


def test_aggregate_403_without_access(
    client: TestClient, kaoriq_key: str, mypcrig_key: str
) -> None:
    persona_id = client.post(
        "/personas", json=fragrance_payload(), headers={"X-API-Key": kaoriq_key}
    ).json()["persona_id"]

    res = client.get(
        f"/personas/{persona_id}/aggregate",
        headers={"X-API-Key": mypcrig_key},
    )
    assert res.status_code == 403
