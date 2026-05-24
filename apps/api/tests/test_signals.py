"""Tests for ``POST /personas/:id/signals``."""

from fastapi.testclient import TestClient

from .conftest import fragrance_payload, pc_payload


def _create(client: TestClient, key: str) -> str:
    res = client.post("/personas", json=fragrance_payload(), headers={"X-API-Key": key})
    return str(res.json()["persona_id"])


def test_creator_can_append_signal(client: TestClient, kaoriq_key: str) -> None:
    """kaoriq can re-record its own profile (a re-quiz) under the same persona."""
    persona_id = _create(client, kaoriq_key)
    res = client.post(
        f"/personas/{persona_id}/signals",
        json=fragrance_payload(),
        headers={"X-API-Key": kaoriq_key},
    )
    assert res.status_code == 201
    assert res.json() == {"ok": True}

    get_res = client.get(f"/personas/{persona_id}", headers={"X-API-Key": kaoriq_key})
    assert len(get_res.json()["signals"]) == 2


def test_other_key_without_token_rejected(
    client: TestClient, kaoriq_key: str, mypcrig_key: str
) -> None:
    persona_id = _create(client, kaoriq_key)
    res = client.post(
        f"/personas/{persona_id}/signals",
        json=pc_payload(),
        headers={"X-API-Key": mypcrig_key},
    )
    assert res.status_code == 403


def test_signal_404_for_missing_persona(client: TestClient, kaoriq_key: str) -> None:
    res = client.post(
        "/personas/01ARZ3NDEKTSV4RRFFQ69G5FAV/signals",
        json=fragrance_payload(),
        headers={"X-API-Key": kaoriq_key},
    )
    assert res.status_code == 404


def test_signal_rejects_source_spoof(client: TestClient, kaoriq_key: str) -> None:
    persona_id = _create(client, kaoriq_key)
    res = client.post(
        f"/personas/{persona_id}/signals",
        json=pc_payload(),  # source='mypcrig' but auth is kaoriq
        headers={"X-API-Key": kaoriq_key},
    )
    assert res.status_code == 400
    assert "source must match" in res.json()["detail"]


def test_signal_whitelist_enforced(
    client: TestClient, kaoriq_key: str, fragrance_only_key: str
) -> None:
    persona_id = _create(client, kaoriq_key)
    token_res = client.post(
        f"/personas/{persona_id}/handoff_token",
        headers={"X-API-Key": kaoriq_key},
    )
    token = token_res.json()["token"]

    # fragrance_only_key has allowed_profile_ids=['fragrance.v1']; try to write pc.v1.
    bad = pc_payload(source="fragrance-only")
    res = client.post(
        f"/personas/{persona_id}/signals",
        json=bad,
        headers={
            "X-API-Key": fragrance_only_key,
            "Authorization": f"Bearer {token}",
        },
    )
    assert res.status_code == 403
    assert "not allowed to write profile_id" in res.json()["detail"]
