"""Pydantic request/response models for the API surface."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SignalIn(BaseModel):
    """Common shape for signal data accepted by both ``POST /personas``
    (creating a persona with its first signal) and ``POST /personas/{id}/signals``
    (appending a subsequent signal).
    """

    source: str = Field(..., min_length=1, max_length=64)
    profile_id: str = Field(..., min_length=1, max_length=128)
    profile_version: str = Field(..., min_length=1, max_length=32)
    scoring_version: str = Field(..., min_length=1, max_length=32)
    result: dict[str, Any]
    answers: dict[str, Any] | None = None


class PersonaCreated(BaseModel):
    persona_id: str


class SignalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source: str
    profile_id: str
    profile_version: str
    scoring_version: str
    result: dict[str, Any]
    created_at: datetime


class PersonaOut(BaseModel):
    persona_id: str
    signals: list[SignalOut]
    aggregate: dict[str, Any] | None = None


class HandoffTokenOut(BaseModel):
    token: str
    persona_id: str
    expires_in: int


class AggregateOut(BaseModel):
    """Aggregated cross-source persona estimate.

    ``placeholder`` is ``True`` only when no contributing signals were found.
    ``scoring_version`` identifies the aggregation engine that produced the
    estimate so downstream consumers can detect logic changes.
    ``source_signals`` records the signal ids that contributed, for audit
    and debugging.
    """

    persona_id: str
    big_five_estimate: dict[str, int] | None = None
    summary: str | None = None
    source_signals: list[str] = Field(default_factory=list)
    scoring_version: str | None = None
    placeholder: bool = True


class OkResponse(BaseModel):
    ok: bool = True
