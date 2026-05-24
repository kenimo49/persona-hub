"""Persona creation, read, aggregate, and handoff-token routes."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.aggregate import BIGFIVE_SCORING_VERSION, compute_bigfive_estimate
from app.config import get_settings
from app.db import get_db
from app.deps import get_api_key, grant_access, require_persona_access
from app.ids import new_ulid
from app.models import HandoffJti, Persona, SourceApiKey
from app.schemas import (
    AggregateOut,
    HandoffTokenOut,
    PersonaCreated,
    PersonaOut,
    SignalIn,
    SignalOut,
)
from app.security import encode_handoff_token
from app.signals_builder import build_signal
from app.validators import (
    check_profile_whitelist,
    check_source_matches_key,
    get_persona_or_404,
)

router = APIRouter()


@router.post(
    "/personas",
    response_model=PersonaCreated,
    status_code=status.HTTP_201_CREATED,
)
def create_persona(
    body: SignalIn,
    db: Annotated[Session, Depends(get_db)],
    api_key: Annotated[SourceApiKey, Depends(get_api_key)],
) -> PersonaCreated:
    """Create a persona and persist its first signal in one transaction."""
    check_source_matches_key(api_key, body.source)
    check_profile_whitelist(api_key, body.profile_id)
    now = datetime.now(UTC)
    persona = Persona(
        id=new_ulid(),
        created_at=now,
        created_by_api_key_id=api_key.id,
    )
    db.add(persona)
    db.add(build_signal(body=body, persona_id=persona.id, api_key_id=api_key.id, now=now))
    grant_access(db, persona.id, api_key.id, via="creator")
    db.commit()
    return PersonaCreated(persona_id=persona.id)


@router.get("/personas/{persona_id}", response_model=PersonaOut)
def get_persona(
    persona_id: str,
    db: Annotated[Session, Depends(get_db)],
    api_key: Annotated[SourceApiKey, Depends(get_api_key)],
    authorization: Annotated[str | None, Header()] = None,
) -> PersonaOut:
    persona = get_persona_or_404(db, persona_id)
    require_persona_access(persona_id, db, api_key, authorization)
    db.commit()
    return PersonaOut(
        persona_id=persona.id,
        signals=[SignalOut.model_validate(s) for s in persona.signals],
        aggregate=None,
    )


@router.get("/personas/{persona_id}/aggregate", response_model=AggregateOut)
def get_aggregate(
    persona_id: str,
    db: Annotated[Session, Depends(get_db)],
    api_key: Annotated[SourceApiKey, Depends(get_api_key)],
    authorization: Annotated[str | None, Header()] = None,
) -> AggregateOut:
    """Return an aggregated cross-source estimate for ``persona_id``.

    The MVP aggregation engine recognizes the ``bigfive.v1`` framework profile.
    When the persona has one or more ``bigfive.v1`` signals, the most recent
    one is used to populate ``big_five_estimate``:

      - If the signal carries ``answers``, the server re-scores using the
        bundled question bank for integrity.
      - Otherwise the signal's pre-evaluated ``result`` is used, after a
        shape check.

    Domain-typed signals (e.g. ``fragrance.v1``, ``pc.v1``) are not yet
    translated into framework estimates — that translation layer is a
    follow-up issue. They are still counted as ``source_signals`` so
    consumers can see they exist.
    """
    persona = get_persona_or_404(db, persona_id)
    require_persona_access(persona_id, db, api_key, authorization)
    db.commit()

    big_five, contributing_id = compute_bigfive_estimate(persona.signals)
    source_signals = [contributing_id] if contributing_id is not None else []
    has_estimate = big_five is not None
    return AggregateOut(
        persona_id=persona.id,
        big_five_estimate=dict(big_five) if big_five is not None else None,
        source_signals=source_signals,
        scoring_version=BIGFIVE_SCORING_VERSION if has_estimate else None,
        placeholder=not has_estimate,
    )


@router.post(
    "/personas/{persona_id}/handoff_token",
    response_model=HandoffTokenOut,
    status_code=status.HTTP_201_CREATED,
)
def issue_handoff_token(
    persona_id: str,
    db: Annotated[Session, Depends(get_db)],
    api_key: Annotated[SourceApiKey, Depends(get_api_key)],
) -> HandoffTokenOut:
    """Issue a short-lived signed token for cross-source persona handoff.

    The issuer must already have access (creator or previously consumed token).
    The receiving service exchanges this token by sending it as
    ``Authorization: Bearer ...`` on a subsequent request to any persona endpoint.
    """
    get_persona_or_404(db, persona_id)
    require_persona_access(persona_id, db, api_key, authorization=None)

    jti = new_ulid()
    token, exp = encode_handoff_token(persona_id, api_key.id, jti)
    db.add(
        HandoffJti(
            jti=jti,
            persona_id=persona_id,
            issued_by_api_key_id=api_key.id,
            issued_at=datetime.now(UTC),
            expires_at=exp,
        )
    )
    db.commit()
    return HandoffTokenOut(
        token=token,
        persona_id=persona_id,
        expires_in=get_settings().handoff_token_ttl_seconds,
    )
