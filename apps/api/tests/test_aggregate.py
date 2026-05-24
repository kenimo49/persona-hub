"""Tests for ``GET /personas/:id/aggregate``."""

from fastapi.testclient import TestClient

from .conftest import bigfive_payload, fragrance_payload


def test_aggregate_returns_placeholder_when_no_bigfive(
    client: TestClient, kaoriq_key: str
) -> None:
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
    assert body["scoring_version"] is None
    assert body["source_signals"] == []


def test_aggregate_surfaces_bigfive_result(
    client: TestClient, kaoriq_key: str
) -> None:
    """A bigfive.v1 signal with only ``result`` (no answers) is passed through."""
    persona_id = client.post(
        "/personas", json=bigfive_payload(), headers={"X-API-Key": kaoriq_key}
    ).json()["persona_id"]

    res = client.get(
        f"/personas/{persona_id}/aggregate",
        headers={"X-API-Key": kaoriq_key},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["placeholder"] is False
    assert body["big_five_estimate"] == {
        "openness": 80,
        "conscientiousness": 70,
        "extraversion": 60,
        "agreeableness": 65,
        "neuroticism": 30,
    }
    assert body["scoring_version"] == "bigfive-0.1.0"
    assert len(body["source_signals"]) == 1


def test_aggregate_recomputes_when_answers_present(
    client: TestClient, kaoriq_key: str
) -> None:
    """When answers are stored, the server re-scores for integrity."""
    persona_id = client.post(
        "/personas",
        json=bigfive_payload(with_answers=True),
        headers={"X-API-Key": kaoriq_key},
    ).json()["persona_id"]

    res = client.get(
        f"/personas/{persona_id}/aggregate",
        headers={"X-API-Key": kaoriq_key},
    )
    assert res.status_code == 200
    body = res.json()
    # answers say openness=100 (4 positive items at 5); the result field's 80
    # should be ignored because the server re-scored from answers.
    assert body["big_five_estimate"]["openness"] == 100
    assert body["placeholder"] is False


def test_aggregate_picks_latest_bigfive_signal(
    client: TestClient, kaoriq_key: str
) -> None:
    """Multiple bigfive signals: the most recent one is used."""
    persona_id = client.post(
        "/personas", json=bigfive_payload(), headers={"X-API-Key": kaoriq_key}
    ).json()["persona_id"]

    # Append a second bigfive signal with a different score
    second = bigfive_payload()
    second["result"] = {
        "openness": 10,
        "conscientiousness": 10,
        "extraversion": 10,
        "agreeableness": 10,
        "neuroticism": 10,
    }
    client.post(
        f"/personas/{persona_id}/signals",
        json=second,
        headers={"X-API-Key": kaoriq_key},
    )

    res = client.get(
        f"/personas/{persona_id}/aggregate",
        headers={"X-API-Key": kaoriq_key},
    )
    assert res.json()["big_five_estimate"]["openness"] == 10


def test_aggregate_ignores_bigfive_with_malformed_result(
    client: TestClient, kaoriq_key: str
) -> None:
    """A signal with bigfive.v1 profile but non-OCEAN result shape returns placeholder."""
    bad = bigfive_payload()
    bad["result"] = {"some_other_shape": True}
    persona_id = client.post(
        "/personas", json=bad, headers={"X-API-Key": kaoriq_key}
    ).json()["persona_id"]

    res = client.get(
        f"/personas/{persona_id}/aggregate",
        headers={"X-API-Key": kaoriq_key},
    )
    body = res.json()
    assert body["big_five_estimate"] is None
    assert body["placeholder"] is True


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
