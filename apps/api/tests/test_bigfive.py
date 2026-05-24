"""Unit tests for the BigFive scoring function."""

from app.aggregate import BIGFIVE_TRAITS, score_bigfive
from app.aggregate.bigfive import coerce_result, is_bigfive_result_shape


def test_score_bigfive_no_answers_returns_neutral() -> None:
    result = score_bigfive({})
    for trait in BIGFIVE_TRAITS:
        assert result[trait] == 50  # type: ignore[literal-required]


def test_score_bigfive_max_positive_items_yields_100() -> None:
    """Four positive openness items at score 5 → openness 100."""
    answers = {"bf_q01": 5, "bf_q02": 5, "bf_q03": 5, "bf_q04": 5}
    result = score_bigfive(answers)
    assert result["openness"] == 100
    # Untouched traits remain neutral
    assert result["conscientiousness"] == 50


def test_score_bigfive_reverse_keyed_item_is_mirrored() -> None:
    """bf_q05 is a reverse-keyed openness item; 5 → effective 1 → score 0."""
    result = score_bigfive({"bf_q05": 5})
    assert result["openness"] == 0


def test_score_bigfive_mixed_positive_and_reverse() -> None:
    """Two positive 5s and one reverse 1 (=effective 5) → all max → mean 5 → 100."""
    answers = {"bf_q01": 5, "bf_q02": 5, "bf_q05": 1}
    result = score_bigfive(answers)
    assert result["openness"] == 100


def test_score_bigfive_accepts_list_form() -> None:
    """Legacy persona-manager records answers as a list of dicts."""
    answers = [
        {"question_id": "bf_q01", "score": 4},
        {"question_id": "bf_q02", "score": 4},
    ]
    result = score_bigfive(answers)
    assert result["openness"] == round((4 - 1) * 25)  # = 75


def test_score_bigfive_ignores_unknown_question_ids() -> None:
    result = score_bigfive({"nonexistent_q": 5, "bf_q01": 5})
    # Only bf_q01 (4 positive items in trait pool, here only 1 answered) contributes
    assert result["openness"] == 100


def test_score_bigfive_clips_out_of_range_scores() -> None:
    """Pathological scores are clipped to [1, 5]."""
    assert score_bigfive({"bf_q01": 999})["openness"] == 100
    assert score_bigfive({"bf_q01": -5})["openness"] == 0


def test_score_bigfive_ignores_malformed_entries() -> None:
    """Non-string keys and non-numeric scores are silently dropped."""
    bad = {"bf_q01": "not a number", 42: 5}
    result = score_bigfive(bad)
    for trait in BIGFIVE_TRAITS:
        assert result[trait] == 50  # type: ignore[literal-required]


def test_score_bigfive_ignores_unknown_input_types() -> None:
    """Non-dict, non-list inputs must not crash; return neutral."""
    result = score_bigfive(42)
    for trait in BIGFIVE_TRAITS:
        assert result[trait] == 50  # type: ignore[literal-required]


def test_is_bigfive_result_shape_accepts_full_dict() -> None:
    assert is_bigfive_result_shape(
        {
            "openness": 70,
            "conscientiousness": 60,
            "extraversion": 55,
            "agreeableness": 65,
            "neuroticism": 40,
        }
    )


def test_is_bigfive_result_shape_rejects_missing_trait() -> None:
    assert not is_bigfive_result_shape(
        {"openness": 70, "conscientiousness": 60, "extraversion": 55, "agreeableness": 65}
    )


def test_is_bigfive_result_shape_rejects_non_dict() -> None:
    assert not is_bigfive_result_shape([1, 2, 3])
    assert not is_bigfive_result_shape("not a dict")


def test_coerce_result_returns_typed_dict() -> None:
    raw = {
        "openness": 70.0,  # int-coercible float
        "conscientiousness": 60,
        "extraversion": 55,
        "agreeableness": 65,
        "neuroticism": 40,
    }
    coerced = coerce_result(raw)
    assert coerced is not None
    assert coerced["openness"] == 70
    assert coerced["neuroticism"] == 40


def test_coerce_result_returns_none_on_bad_shape() -> None:
    assert coerce_result({"openness": 70}) is None
    assert coerce_result(None) is None


def test_is_bigfive_result_shape_rejects_boolean_values() -> None:
    """``isinstance(True, int)`` is True, so we must explicitly reject bools."""
    payload = {
        "openness": True,
        "conscientiousness": 60,
        "extraversion": 55,
        "agreeableness": 65,
        "neuroticism": 40,
    }
    assert not is_bigfive_result_shape(payload)
    assert coerce_result(payload) is None


def test_score_bigfive_rejects_boolean_scores() -> None:
    """Boolean Likert scores must not be coerced to 0/1 silently."""
    answers = {"bf_q01": True, "bf_q02": False, "bf_q03": 5, "bf_q04": 5}
    result = score_bigfive(answers)
    # Only bf_q03 and bf_q04 should count; both at 5 → openness 100
    assert result["openness"] == 100


def test_score_bigfive_rounds_float_scores_instead_of_truncating() -> None:
    """4.9 must round up to 5, not be truncated to 4."""
    result = score_bigfive({"bf_q01": 4.9})
    # rounded → 5, mean=5, → (5-1)*25 = 100
    assert result["openness"] == 100


def test_coerce_result_rounds_floats_half_up() -> None:
    """Coercion uses ROUND_HALF_UP, so .5 always rounds up regardless of parity."""
    payload = {
        "openness": 70.6,
        "conscientiousness": 60.4,
        "extraversion": 55.5,
        "agreeableness": 64.5,
        "neuroticism": 40.0,
    }
    coerced = coerce_result(payload)
    assert coerced is not None
    assert coerced["openness"] == 71
    assert coerced["conscientiousness"] == 60
    # ROUND_HALF_UP: both .5 values round up regardless of even/odd
    assert coerced["extraversion"] == 56
    assert coerced["agreeableness"] == 65
    assert coerced["neuroticism"] == 40


def test_score_bigfive_uses_half_up_rounding() -> None:
    """An average that lands on .5 must round up, not to the nearest even."""
    # Two answers averaging to 2.5 → effective mean 2.5 → (2.5-1)*25 = 37.5 → 38
    result = score_bigfive({"bf_q01": 2, "bf_q02": 3})
    assert result["openness"] == 38


def test_score_bigfive_rejects_nan_and_inf() -> None:
    """Non-finite float scores must not crash the scoring path."""
    result = score_bigfive(
        {
            "bf_q01": float("nan"),
            "bf_q02": float("inf"),
            "bf_q03": float("-inf"),
        }
    )
    for trait in BIGFIVE_TRAITS:
        assert result[trait] == 50  # type: ignore[literal-required]


def test_coerce_result_rejects_nan_and_inf() -> None:
    """Non-finite trait values in a result payload yield None instead of crashing."""
    payload = {
        "openness": float("nan"),
        "conscientiousness": 60,
        "extraversion": 55,
        "agreeableness": 65,
        "neuroticism": 40,
    }
    assert coerce_result(payload) is None
    assert not is_bigfive_result_shape(payload)

    payload["openness"] = float("inf")
    assert coerce_result(payload) is None
    assert not is_bigfive_result_shape(payload)
