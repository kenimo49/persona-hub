"""Internal aggregation engine for ``GET /aggregate``.

Each submodule implements a single framework's scoring logic ported from the
legacy private ``kenimo49/persona-manager`` codebase. The functions here are
pure and deterministic — they take answers, return scored results — so callers
can use them either to re-evaluate server-side for integrity or to power
offline scripts.
"""

from app.aggregate.bigfive import (
    BIGFIVE_PROFILE_ID,
    BIGFIVE_SCORING_VERSION,
    BIGFIVE_TRAITS,
    BigFiveResult,
    is_bigfive_result_shape,
    score_bigfive,
)

__all__ = [
    "BIGFIVE_PROFILE_ID",
    "BIGFIVE_SCORING_VERSION",
    "BIGFIVE_TRAITS",
    "BigFiveResult",
    "is_bigfive_result_shape",
    "score_bigfive",
]
