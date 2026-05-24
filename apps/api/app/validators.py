"""Request-level guards shared by router modules.

Centralises the source-spoofing check and the per-key profile whitelist so both
``personas`` and ``signals`` routers stay consistent if the policy evolves.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Persona, SourceApiKey


def check_source_matches_key(api_key: SourceApiKey, source: str) -> None:
    """Bind the client-supplied ``source`` field to the authenticated API key.

    Without this check a holder of one key could attribute writes to a sibling
    service ("spoof writes as a legitimate source service" in the threat model).
    """
    if source != api_key.name:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"source must match the authenticated API key (expected {api_key.name!r})",
        )


def check_profile_whitelist(api_key: SourceApiKey, profile_id: str) -> None:
    """Enforce ``allowed_profile_ids`` if the key has a non-empty whitelist."""
    if api_key.allowed_profile_ids and profile_id not in api_key.allowed_profile_ids:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"API key not allowed to write profile_id={profile_id}",
        )


def get_persona_or_404(db: Session, persona_id: str) -> Persona:
    """Load a persona by id or raise 404. Avoids the repeated ``db.get`` + ``if None`` pattern."""
    persona = db.get(Persona, persona_id)
    if persona is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Persona not found")
    return persona
