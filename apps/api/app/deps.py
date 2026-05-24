"""FastAPI dependencies: authentication and persona access checks."""

from datetime import UTC, datetime
from typing import Annotated, Any, cast

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import CursorResult, select, update
from sqlalchemy.orm import Session

from app.db import get_db
from app.ids import API_KEY_LOOKUP_LEN, api_key_lookup_prefix
from app.models import HandoffJti, PersonaAccess, SourceApiKey
from app.security import decode_handoff_token, verify_api_key


def get_api_key(
    db: Annotated[Session, Depends(get_db)],
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> SourceApiKey:
    """Authenticate the caller via the ``X-API-Key`` header.

    Raises 401 on a missing, malformed, disabled, or unknown key.
    """
    if not x_api_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing X-API-Key header")
    if len(x_api_key) < API_KEY_LOOKUP_LEN:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key format")
    prefix = api_key_lookup_prefix(x_api_key)
    key_row = db.execute(
        select(SourceApiKey).where(SourceApiKey.key_prefix == prefix)
    ).scalar_one_or_none()
    if key_row is None or key_row.disabled:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")
    if not verify_api_key(x_api_key, key_row.key_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")
    return key_row


def grant_access(db: Session, persona_id: str, api_key_id: str, via: str) -> None:
    """Idempotently add a ``PersonaAccess`` row. Caller is responsible for ``commit()``."""
    existing = db.execute(
        select(PersonaAccess).where(
            PersonaAccess.persona_id == persona_id,
            PersonaAccess.api_key_id == api_key_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return
    db.add(
        PersonaAccess(
            persona_id=persona_id,
            api_key_id=api_key_id,
            granted_at=datetime.now(UTC),
            granted_via=via,
        )
    )


def require_persona_access(
    persona_id: str,
    db: Session,
    api_key: SourceApiKey,
    authorization: str | None,
) -> None:
    """Ensure ``api_key`` may operate on ``persona_id``.

    Path 1: the key already appears in ``persona_access`` → allowed.

    Path 2: a valid ``Authorization: Bearer <handoff_jwt>`` header is present
    and references this persona → the token is marked consumed and the
    calling key is added to ``persona_access`` for future requests.

    Otherwise raises 403. Caller commits the surrounding transaction.
    """
    has_access = db.execute(
        select(PersonaAccess).where(
            PersonaAccess.persona_id == persona_id,
            PersonaAccess.api_key_id == api_key.id,
        )
    ).scalar_one_or_none()
    if has_access is not None:
        return

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No access to this persona")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Empty handoff token")

    try:
        claims = decode_handoff_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Handoff token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid handoff token") from exc

    if claims["sub"] != persona_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Handoff token subject mismatch")

    jti_row = db.execute(
        select(HandoffJti).where(HandoffJti.jti == claims["jti"])
    ).scalar_one_or_none()
    if jti_row is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Unknown handoff token")
    if jti_row.persona_id != persona_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Token persona mismatch")
    if jti_row.issued_by_api_key_id != claims["iss_key"]:
        # Defense in depth: the signed claim must agree with the persisted issuer.
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Token issuer mismatch")

    # Atomic single-use consume: this UPDATE matches at most one row, and only
    # when the token has not been consumed yet. Two concurrent requests cannot
    # both succeed because the second one's WHERE clause will match zero rows.
    now = datetime.now(UTC)
    # ``Session.execute(update(...))`` returns a ``CursorResult`` at runtime,
    # but the inferred type is the generic ``Result``. Narrow it once so
    # ``rowcount`` access is statically typed without a per-call ignore.
    cursor = cast(
        CursorResult[Any],
        db.execute(
            update(HandoffJti)
            .where(
                HandoffJti.jti == claims["jti"],
                HandoffJti.consumed_at.is_(None),
            )
            .values(consumed_at=now, consumed_by_api_key_id=api_key.id)
        ),
    )
    if cursor.rowcount == 0:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Handoff token already consumed")
    grant_access(db, persona_id, api_key.id, via="handoff_token")
