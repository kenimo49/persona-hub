"""Service-layer aggregation helpers.

Keeps the cross-signal selection and re-scoring policy out of HTTP routers, so
the policy can be unit-tested without spinning up FastAPI.
"""

from app.aggregate.bigfive import (
    BIGFIVE_PROFILE_ID,
    BigFiveResult,
    coerce_result,
    score_bigfive,
)
from app.models import Signal


def compute_bigfive_estimate(
    signals: list[Signal],
) -> tuple[BigFiveResult | None, str | None]:
    """Find the most recent ``bigfive.v1`` signal and produce a 0-100 OCEAN estimate.

    Returns ``(estimate, contributing_signal_id)`` or ``(None, None)`` if no
    usable signal is available. When the signal carries ``answers`` the server
    re-scores using the bundled BigFive question bank for integrity; otherwise
    the pre-evaluated ``result`` is passed through after a shape check.
    """
    bigfive_signals = [s for s in signals if s.profile_id == BIGFIVE_PROFILE_ID]
    if not bigfive_signals:
        return None, None
    latest = max(bigfive_signals, key=lambda s: s.created_at)

    if latest.answers is not None:
        return score_bigfive(latest.answers), latest.id

    coerced = coerce_result(latest.result)
    if coerced is not None:
        return coerced, latest.id
    return None, None
