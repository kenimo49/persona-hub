"""Signal append route."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_api_key, require_persona_access
from app.models import SourceApiKey
from app.schemas import OkResponse, SignalIn
from app.signals_builder import build_signal
from app.validators import (
    check_profile_whitelist,
    check_source_matches_key,
    get_persona_or_404,
)

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
    get_persona_or_404(db, persona_id)
    require_persona_access(persona_id, db, api_key, authorization)
    check_source_matches_key(api_key, body.source)
    check_profile_whitelist(api_key, body.profile_id)

    now = datetime.now(UTC)
    db.add(build_signal(body=body, persona_id=persona_id, api_key_id=api_key.id, now=now))
    db.commit()
    return OkResponse(ok=True)
