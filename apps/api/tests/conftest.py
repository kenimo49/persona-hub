"""Shared pytest fixtures.

We must set environment variables that influence ``get_settings()`` *before*
importing the application, since the settings object is ``lru_cache``-d and the
slowapi limiter reads ``enable_rate_limit`` once at construction time.
"""

import os
from collections.abc import Generator
from datetime import UTC, datetime

import pytest

os.environ.setdefault("PH_ENABLE_RATE_LIMIT", "false")
os.environ.setdefault(
    "PH_JWT_SECRET",
    "test-secret-do-not-use-in-prod-must-be-at-least-32-bytes-long",
)

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db import get_db  # noqa: E402
from app.ids import api_key_lookup_prefix, new_api_key, new_ulid  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base, SourceApiKey  # noqa: E402
from app.security import hash_api_key  # noqa: E402


@pytest.fixture
def db_engine() -> Generator[Engine, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(db_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=db_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


@pytest.fixture
def db_session(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _seed_api_key(
    db: Session, name: str, *, allowed: list[str] | None = None, disabled: bool = False
) -> str:
    raw = new_api_key()
    db.add(
        SourceApiKey(
            id=new_ulid(),
            name=name,
            key_prefix=api_key_lookup_prefix(raw),
            key_hash=hash_api_key(raw),
            allowed_profile_ids=allowed or [],
            disabled=disabled,
            created_at=datetime.now(UTC),
        )
    )
    db.commit()
    return raw


@pytest.fixture
def kaoriq_key(db_session: Session) -> str:
    return _seed_api_key(db_session, "kaoriq")


@pytest.fixture
def mypcrig_key(db_session: Session) -> str:
    return _seed_api_key(db_session, "mypcrig")


@pytest.fixture
def fragrance_only_key(db_session: Session) -> str:
    return _seed_api_key(db_session, "fragrance-only", allowed=["fragrance.v1"])


@pytest.fixture
def disabled_key(db_session: Session) -> str:
    return _seed_api_key(db_session, "disabled-key", disabled=True)


def fragrance_payload(source: str = "kaoriq") -> dict[str, object]:
    """Build a fragrance-profile signal payload for tests."""
    return {
        "source": source,
        "profile_id": "fragrance.v1",
        "profile_version": "1.0.0",
        "scoring_version": "core-0.1.0",
        "result": {"type": "citrus", "scores": {"citrus": 0.9}},
    }


def pc_payload(source: str = "mypcrig") -> dict[str, object]:
    """Build a PC-profile signal payload for tests."""
    return {
        "source": source,
        "profile_id": "pc.v1",
        "profile_version": "1.0.0",
        "scoring_version": "core-0.1.0",
        "result": {"type": "minimal-silent", "scores": {"minimal-silent": 0.8}},
    }


def bigfive_payload(
    source: str = "kaoriq",
    *,
    with_answers: bool = False,
) -> dict[str, object]:
    """Build a bigfive.v1 signal payload for tests.

    When ``with_answers=True`` includes four high-openness Likert answers so a
    server-side re-score yields openness=100. Useful for testing the integrity
    path in ``GET /aggregate``.
    """
    payload: dict[str, object] = {
        "source": source,
        "profile_id": "bigfive.v1",
        "profile_version": "1.0.0",
        "scoring_version": "bigfive-0.1.0",
        "result": {
            "openness": 80,
            "conscientiousness": 70,
            "extraversion": 60,
            "agreeableness": 65,
            "neuroticism": 30,
        },
    }
    if with_answers:
        payload["answers"] = {"bf_q01": 5, "bf_q02": 5, "bf_q03": 5, "bf_q04": 5}
    return payload


def create_persona(
    client: TestClient, key: str, *, payload: dict[str, object] | None = None
) -> str:
    """Shortcut: POST /personas and return the new persona_id.

    Defaults to a kaoriq fragrance payload — most cross-source tests just need
    a persona to exist before exercising the path under test.
    """
    body = payload if payload is not None else fragrance_payload()
    res = client.post("/personas", json=body, headers={"X-API-Key": key})
    return str(res.json()["persona_id"])
