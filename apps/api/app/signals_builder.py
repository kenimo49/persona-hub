"""Single construction site for ``Signal`` rows.

The persona-create and signal-append paths used to inline the same
``Signal(...)`` constructor; centralising it here means any future column or
default lives in exactly one place.
"""

from datetime import datetime

from app.ids import new_ulid
from app.models import Signal
from app.schemas import SignalIn


def build_signal(
    *,
    body: SignalIn,
    persona_id: str,
    api_key_id: str,
    now: datetime,
) -> Signal:
    return Signal(
        id=new_ulid(),
        persona_id=persona_id,
        source=body.source,
        profile_id=body.profile_id,
        profile_version=body.profile_version,
        scoring_version=body.scoring_version,
        result=body.result,
        answers=body.answers,
        created_by_api_key_id=api_key_id,
        created_at=now,
    )
