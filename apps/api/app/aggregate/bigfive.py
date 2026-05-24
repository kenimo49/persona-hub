"""BigFive (OCEAN) scoring.

Ported from the maintainer's private ``persona-manager`` repository:
``apps/persona-web-app/services/bigfive_service.py``. The original Japanese
question items were authored by the same maintainer and are re-licensed
under Apache-2.0 as part of this repository.

Algorithm
---------
- Each question carries a ``trait`` (one of OCEAN) and a ``reverse`` flag.
- Likert scores (1-5) for reverse-keyed items are mirrored via ``6 - score``.
- Per trait we take the mean across answered items, then rescale 1-5 → 0-100
  with ``(mean - 1) * 25``.
- Unanswered traits default to 50 (neutral midpoint).

The function is pure and deterministic — no I/O on the hot path beyond a
one-shot read of the bundled question bank on first use.
"""

import json
import math
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
from importlib import resources
from typing import Any, TypedDict, cast


def _round_half_up(value: float) -> int:
    """Half-up rounding (50.5 → 51).

    Python's built-in ``round()`` uses banker's rounding (round-half-to-even),
    which would make ``round(70.5) == 70``. For user-facing trait scores that's
    surprising, so we use ``Decimal`` with ``ROUND_HALF_UP`` for an explicit,
    well-known policy. Caller must guarantee ``value`` is finite —
    ``_is_numeric`` is the gate that filters NaN and ±inf upstream.
    """
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

BIGFIVE_PROFILE_ID = "bigfive.v1"
BIGFIVE_SCORING_VERSION = "bigfive-0.1.0"

BIGFIVE_TRAITS: tuple[str, ...] = (
    "openness",
    "conscientiousness",
    "extraversion",
    "agreeableness",
    "neuroticism",
)


class BigFiveResult(TypedDict):
    openness: int
    conscientiousness: int
    extraversion: int
    agreeableness: int
    neuroticism: int


class _QuestionMeta(TypedDict):
    trait: str
    reverse: bool


@lru_cache(maxsize=1)
def _question_bank() -> dict[str, _QuestionMeta]:
    """Read the bundled BigFive question bank once and index it by question id."""
    raw_text = (resources.files("app.aggregate") / "data" / "bigfive_questions.json").read_text(
        encoding="utf-8"
    )
    raw = json.loads(raw_text)
    bank: dict[str, _QuestionMeta] = {}
    for q in raw["questions"]:
        bank[q["id"]] = _QuestionMeta(trait=q["trait"], reverse=bool(q.get("reverse", False)))
    return bank


def _neutral_result() -> BigFiveResult:
    return BigFiveResult(
        openness=50,
        conscientiousness=50,
        extraversion=50,
        agreeableness=50,
        neuroticism=50,
    )


def _is_numeric(value: object) -> bool:
    """Return True for finite numeric inputs.

    Filters out:
      - ``bool`` (a subclass of ``int`` in Python; ``True`` would silently
        coerce to a score of 1, ``False`` to 0)
      - ``NaN`` and ``±inf`` (would crash the ``Decimal`` rounding step
        downstream)
    """
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    return False


def _coerce_score(value: object) -> int | None:
    """Convert a Likert score input to ``int`` via half-up rounding.

    Returns ``None`` for non-numeric or boolean input. Floats are rounded
    (4.9 → 5, not truncated to 4; 4.5 → 5 deterministically via half-up).
    """
    if not _is_numeric(value):
        return None
    return _round_half_up(float(value))  # type: ignore[arg-type]


def _normalize_answers(answers: object) -> dict[str, int]:
    """Accept either ``{qid: score}`` or ``[{question_id, score}, ...]``.

    Silently drops malformed entries; the function is intentionally lenient
    because answers may have been recorded under an earlier schema. Booleans
    are explicitly rejected (Python treats ``True/False`` as 1/0 by default,
    which would silently corrupt scoring).
    """
    out: dict[str, int] = {}
    if isinstance(answers, dict):
        for k, v in answers.items():
            score = _coerce_score(v)
            if isinstance(k, str) and score is not None:
                out[k] = score
        return out
    if isinstance(answers, list):
        for entry in answers:
            if not isinstance(entry, dict):
                continue
            qid = entry.get("question_id")
            score = _coerce_score(entry.get("score"))
            if isinstance(qid, str) and score is not None:
                out[qid] = score
        return out
    return out


def score_bigfive(answers: object) -> BigFiveResult:
    """Compute OCEAN scores from Likert answers.

    Returns a ``BigFiveResult`` with 0-100 score per trait. Unknown
    ``question_id`` values and non-numeric scores are ignored.
    """
    bank = _question_bank()
    normalized = _normalize_answers(answers)

    trait_scores: dict[str, list[float]] = {t: [] for t in BIGFIVE_TRAITS}
    for qid, score in normalized.items():
        meta = bank.get(qid)
        if meta is None:
            continue
        if meta["trait"] not in trait_scores:
            continue
        clipped = max(1, min(5, score))
        effective = (6 - clipped) if meta["reverse"] else clipped
        trait_scores[meta["trait"]].append(float(effective))

    result = _neutral_result()
    for trait in BIGFIVE_TRAITS:
        scores = trait_scores[trait]
        if scores:
            mean = sum(scores) / len(scores)
            result[trait] = _round_half_up((mean - 1) * 25)  # type: ignore[literal-required]
    return result


def is_bigfive_result_shape(value: object) -> bool:
    """Return True if ``value`` is a plain dict containing all five OCEAN traits.

    Boolean values are rejected even though ``isinstance(True, int)`` is True,
    so a payload like ``{"openness": True, ...}`` cannot be silently coerced
    to a valid score of 1.
    """
    if not isinstance(value, dict):
        return False
    for trait in BIGFIVE_TRAITS:
        if trait not in value:
            return False
        if not _is_numeric(value[trait]):
            return False
    return True


def coerce_result(value: object) -> BigFiveResult | None:
    """Return a normalized ``BigFiveResult`` if ``value`` has the expected shape.

    Float trait scores use half-up rounding (70.5 → 71) so that boundary
    values round consistently regardless of the IEEE-754 even-bit value,
    which differs from Python's default banker's ``round()``.
    """
    if not is_bigfive_result_shape(value):
        return None
    typed = cast(dict[str, Any], value)
    return BigFiveResult(
        openness=_round_half_up(float(typed["openness"])),
        conscientiousness=_round_half_up(float(typed["conscientiousness"])),
        extraversion=_round_half_up(float(typed["extraversion"])),
        agreeableness=_round_half_up(float(typed["agreeableness"])),
        neuroticism=_round_half_up(float(typed["neuroticism"])),
    )
