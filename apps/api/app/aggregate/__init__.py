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
    Trait,
    is_bigfive_result_shape,
    score_bigfive,
)
from app.aggregate.service import compute_bigfive_estimate

__all__ = [
    "BIGFIVE_PROFILE_ID",
    "BIGFIVE_SCORING_VERSION",
    "BIGFIVE_TRAITS",
    "BigFiveResult",
    "Trait",
    "compute_bigfive_estimate",
    "is_bigfive_result_shape",
    "score_bigfive",
]
