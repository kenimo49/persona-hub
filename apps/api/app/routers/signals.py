"""Signal append route."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_api_key, require_persona_access
from app.ids import new_ulid
from app.models import Persona, Signal, SourceApiKey
from app.schemas import OkResponse, SignalIn

router = APIRouter()


@router.post(
    "/personas/{persona_id}/signals",
    response_model=OkResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_signal(
    persona_id: str,
    body: SignalIn,
    db: Annotated[Session, Depends(get_db)],
    api_key: Annotated[SourceApiKey, Depends(get_api_key)],
    authorization: Annotated[str | None, Header()] = None,
) -> OkResponse:
    """Append a signal from another source service to an existing persona.

    The caller must have access — either via prior creator/handoff grant, or by
    presenting a still-valid Bearer handoff token in this request.
    """
    persona = db.get(Persona, persona_id)
    if persona is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Persona not found")
    require_persona_access(persona_id, db, api_key, authorization)

    if body.source != api_key.name:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"source must match the authenticated API key (expected {api_key.name!r})",
        )
    if api_key.allowed_profile_ids and body.profile_id not in api_key.allowed_profile_ids:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"API key not allowed to write profile_id={body.profile_id}",
        )

    now = datetime.now(UTC)
    db.add(
        Signal(
            id=new_ulid(),
            persona_id=persona_id,
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
    db.commit()
    return OkResponse(ok=True)
