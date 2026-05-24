"""Persona creation, read, aggregate, and handoff-token routes."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import get_api_key, grant_access, require_persona_access
from app.ids import new_ulid
from app.models import HandoffJti, Persona, Signal, SourceApiKey
from app.schemas import (
    AggregateOut,
    HandoffTokenOut,
    PersonaCreated,
    PersonaOut,
    SignalIn,
    SignalOut,
)
from app.security import encode_handoff_token

router = APIRouter()


def _check_profile_whitelist(api_key: SourceApiKey, profile_id: str) -> None:
    """Enforce ``allowed_profile_ids`` if the key has a non-empty whitelist."""
    if api_key.allowed_profile_ids and profile_id not in api_key.allowed_profile_ids:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"API key not allowed to write profile_id={profile_id}",
        )


def _check_source_matches_key(api_key: SourceApiKey, source: str) -> None:
    """Bind the client-supplied ``source`` field to the authenticated API key.

    Without this check a holder of one key could attribute writes to a sibling
    service ("spoof writes as a legitimate source service" in the threat model).
    """
    if source != api_key.name:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"source must match the authenticated API key (expected {api_key.name!r})",
        )


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
    _check_source_matches_key(api_key, body.source)
    _check_profile_whitelist(api_key, body.profile_id)
    now = datetime.now(UTC)
    persona = Persona(
        id=new_ulid(),
        created_at=now,
        created_by_api_key_id=api_key.id,
    )
    db.add(persona)
    db.add(
        Signal(
            id=new_ulid(),
            persona_id=persona.id,
            source=body.source,
            profile_id=body.profile_id,
            profile_version=body.profile_version,
            scoring_version=body.scoring_version,
            result=body.result,
            answers=body.answers,
            created_by_api_key_id=api_key.id,
            created_at=now,
        )
    )
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
    persona = db.get(Persona, persona_id)
    if persona is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Persona not found")
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
    """Return aggregated cross-source estimate.

    Placeholder until Issue #7 ports the 5-framework scoring engine.
    """
    persona = db.get(Persona, persona_id)
    if persona is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Persona not found")
    require_persona_access(persona_id, db, api_key, authorization)
    db.commit()
    return AggregateOut(persona_id=persona.id, placeholder=True)


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
    persona = db.get(Persona, persona_id)
    if persona is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Persona not found")
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
