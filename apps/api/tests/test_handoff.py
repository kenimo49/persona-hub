"""Tests for the handoff token flow (issue → consume → grant access)."""

from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import HandoffJti

from .conftest import create_persona, pc_payload


def test_issue_handoff_token(client: TestClient, kaoriq_key: str) -> None:
    persona_id = create_persona(client, kaoriq_key)
    res = client.post(
        f"/personas/{persona_id}/handoff_token",
        headers={"X-API-Key": kaoriq_key},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["persona_id"] == persona_id
    assert body["expires_in"] == 300
    assert body["token"].count(".") == 2  # JWT has three segments


def test_handoff_token_required_caller_has_access(
    client: TestClient, kaoriq_key: str, mypcrig_key: str
) -> None:
    persona_id = create_persona(client, kaoriq_key)
    res = client.post(
        f"/personas/{persona_id}/handoff_token",
        headers={"X-API-Key": mypcrig_key},
    )
    assert res.status_code == 403


def test_handoff_token_grants_cross_source_write(
    client: TestClient, kaoriq_key: str, mypcrig_key: str
) -> None:
    persona_id = create_persona(client, kaoriq_key)
    token = client.post(
        f"/personas/{persona_id}/handoff_token",
        headers={"X-API-Key": kaoriq_key},
    ).json()["token"]

    res = client.post(
        f"/personas/{persona_id}/signals",
        json=pc_payload(),
        headers={"X-API-Key": mypcrig_key, "Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201

    # Subsequent calls from mypcrig need no token (access persisted)
    res2 = client.get(f"/personas/{persona_id}", headers={"X-API-Key": mypcrig_key})
    assert res2.status_code == 200
    assert len(res2.json()["signals"]) == 2


def test_handoff_token_single_use_concurrent_consume(
    client: TestClient, kaoriq_key: str, mypcrig_key: str, db_session: Session
) -> None:
    """A second consume attempt with a different key must be rejected (atomic UPDATE)."""
    from app.ids import api_key_lookup_prefix, new_api_key, new_ulid
    from app.models import SourceApiKey
    from app.security import hash_api_key

    raw_third = new_api_key()
    db_session.add(
        SourceApiKey(
            id=new_ulid(),
            name="third-svc",
            key_prefix=api_key_lookup_prefix(raw_third),
            key_hash=hash_api_key(raw_third),
            allowed_profile_ids=[],
            disabled=False,
            created_at=datetime.now(UTC),
        )
    )
    db_session.commit()

    persona_id = create_persona(client, kaoriq_key)
    token = client.post(
        f"/personas/{persona_id}/handoff_token",
        headers={"X-API-Key": kaoriq_key},
    ).json()["token"]

    # First consume succeeds
    first = client.post(
        f"/personas/{persona_id}/signals",
        json=pc_payload(),
        headers={"X-API-Key": mypcrig_key, "Authorization": f"Bearer {token}"},
    )
    assert first.status_code == 201

    # Second consume by another real key fails
    res = client.get(
        f"/personas/{persona_id}",
        headers={"X-API-Key": raw_third, "Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
    assert "already consumed" in res.json()["detail"]


def test_handoff_token_rejects_bad_subject(
    client: TestClient, kaoriq_key: str, mypcrig_key: str
) -> None:
    persona_id_a = create_persona(client, kaoriq_key)
    persona_id_b = create_persona(client, kaoriq_key)
    token = client.post(
        f"/personas/{persona_id_a}/handoff_token",
        headers={"X-API-Key": kaoriq_key},
    ).json()["token"]

    res = client.get(
        f"/personas/{persona_id_b}",
        headers={"X-API-Key": mypcrig_key, "Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
    assert "subject mismatch" in res.json()["detail"]


def test_handoff_token_rejects_expired(
    client: TestClient, kaoriq_key: str, mypcrig_key: str
) -> None:
    persona_id = create_persona(client, kaoriq_key)
    settings = get_settings()
    now = datetime.now(UTC)
    expired = jwt.encode(
        {
            "iss": "persona-hub",
            "jti": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "sub": persona_id,
            "iss_key": "anykey",
            "iat": int((now - timedelta(hours=1)).timestamp()),
            "exp": int((now - timedelta(minutes=30)).timestamp()),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    res = client.get(
        f"/personas/{persona_id}",
        headers={"X-API-Key": mypcrig_key, "Authorization": f"Bearer {expired}"},
    )
    assert res.status_code == 403
    assert "expired" in res.json()["detail"].lower()


def test_handoff_token_rejects_unknown_jti(
    client: TestClient, kaoriq_key: str, mypcrig_key: str
) -> None:
    """Valid signature but jti was never issued (server has no record)."""
    persona_id = create_persona(client, kaoriq_key)
    settings = get_settings()
    now = datetime.now(UTC)
    fabricated = jwt.encode(
        {
            "iss": "persona-hub",
            "jti": "01FAKEFAKEFAKEFAKEFAKEFAKE",
            "sub": persona_id,
            "iss_key": "anykey",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    res = client.get(
        f"/personas/{persona_id}",
        headers={"X-API-Key": mypcrig_key, "Authorization": f"Bearer {fabricated}"},
    )
    assert res.status_code == 403
    assert "Unknown handoff token" in res.json()["detail"]


def test_handoff_token_rejects_issuer_mismatch(
    client: TestClient, kaoriq_key: str, mypcrig_key: str, db_session: Session
) -> None:
    """A signed token whose iss_key disagrees with the stored issuer is rejected."""
    persona_id = create_persona(client, kaoriq_key)
    # Issue a real token so the jti row exists.
    real_token = client.post(
        f"/personas/{persona_id}/handoff_token",
        headers={"X-API-Key": kaoriq_key},
    ).json()["token"]
    decoded = jwt.decode(real_token, options={"verify_signature": False})
    real_jti = decoded["jti"]

    # Forge a token with the same jti but a different iss_key claim.
    settings = get_settings()
    now = datetime.now(UTC)
    forged = jwt.encode(
        {
            "iss": "persona-hub",
            "jti": real_jti,
            "sub": persona_id,
            "iss_key": "some-other-key-id",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    res = client.get(
        f"/personas/{persona_id}",
        headers={"X-API-Key": mypcrig_key, "Authorization": f"Bearer {forged}"},
    )
    assert res.status_code == 403
    assert "issuer mismatch" in res.json()["detail"]


def test_handoff_token_rejects_malformed_authorization(
    client: TestClient, kaoriq_key: str, mypcrig_key: str
) -> None:
    persona_id = create_persona(client, kaoriq_key)
    res = client.get(
        f"/personas/{persona_id}",
        headers={"X-API-Key": mypcrig_key, "Authorization": "Bearer "},
    )
    assert res.status_code == 403


def test_handoff_token_rejects_invalid_signature(
    client: TestClient, kaoriq_key: str, mypcrig_key: str
) -> None:
    persona_id = create_persona(client, kaoriq_key)
    res = client.get(
        f"/personas/{persona_id}",
        headers={"X-API-Key": mypcrig_key, "Authorization": "Bearer not-a-real-jwt"},
    )
    assert res.status_code == 403
    assert "Invalid handoff token" in res.json()["detail"]


def test_handoff_jti_recorded_in_db(
    client: TestClient, kaoriq_key: str, db_session: Session
) -> None:
    persona_id = create_persona(client, kaoriq_key)
    body = client.post(
        f"/personas/{persona_id}/handoff_token",
        headers={"X-API-Key": kaoriq_key},
    ).json()
    decoded = jwt.decode(body["token"], options={"verify_signature": False})
    jti = decoded["jti"]

    row = db_session.get(HandoffJti, jti)
    assert row is not None
    assert row.persona_id == persona_id
    assert row.consumed_at is None
