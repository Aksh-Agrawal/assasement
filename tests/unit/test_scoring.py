"""Direct unit tests for pure scoring behavior."""

import pytest

from app.core.models import Confidence, MarkingScheme, Option, Question, Response
from app.core.scoring import score_attempt


def _question(question_id: str, position: int, correct_key: str = "A") -> Question:
    options = tuple(
        Option(key=key, text=f"Option {key}") for key in ("A", "B", "C", "D")
    )
    return Question(
        id=question_id,
        position=position,
        topic="Test Topic",
        difficulty=1,
        question_text=f"Question {question_id}",
        options=options,
        correct_key=correct_key,  # type: ignore[arg-type]
    )


def _response(
    question_id: str,
    selected_key: str | None,
    confidence: Confidence | None,
    *,
    response_id: str | None = None,
) -> Response:
    return Response(
        id=response_id or f"response-{question_id}",
        attempt_id="attempt-1",
        question_id=question_id,
        selected_key=selected_key,  # type: ignore[arg-type]
        confidence=confidence,
    )


def test_basic_correct_wrong_and_skipped_scoring() -> None:
    questions = {
        "q1": _question("q1", 1, "A"),
        "q2": _question("q2", 2, "B"),
        "q3": _question("q3", 3, "C"),
    }
    responses = [
        _response("q1", "A", Confidence.SURE),
        _response("q2", "D", Confidence.NOT_SURE),
        _response("q3", None, None),
    ]

    result = score_attempt(responses, questions, MarkingScheme())

    assert (result.correct, result.wrong, result.skipped) == (1, 1, 1)
    assert result.attempted == 2
    assert result.score == 3
    assert result.accuracy == 0.5


def test_zero_questions_scores_as_empty_assessment() -> None:
    result = score_attempt([], {}, MarkingScheme())

    assert (result.correct, result.wrong, result.skipped, result.attempted) == (0, 0, 0, 0)
    assert result.score == 0
    assert result.accuracy == 0.0


def test_zero_attempted_has_zero_accuracy() -> None:
    questions = {"q1": _question("q1", 1), "q2": _question("q2", 2)}

    result = score_attempt([_response("q1", None, None)], questions, MarkingScheme())

    assert result.skipped == 2
    assert result.attempted == 0
    assert result.accuracy == 0.0


def test_missing_responses_count_as_skipped() -> None:
    questions = {f"q{i}": _question(f"q{i}", i) for i in range(1, 11)}
    responses = [
        _response(f"q{i}", "A", Confidence.UNRATED) for i in range(1, 7)
    ]

    result = score_attempt(responses, questions, MarkingScheme())

    assert result.correct == 6
    assert result.attempted == 6
    assert result.skipped == 4


def test_custom_marking_scheme_includes_skip_marks() -> None:
    questions = {
        "q1": _question("q1", 1, "A"),
        "q2": _question("q2", 2, "B"),
        "q3": _question("q3", 3, "C"),
    }
    responses = [
        _response("q1", "A", Confidence.SURE),
        _response("q2", "A", Confidence.NOT_SURE),
    ]

    result = score_attempt(
        responses,
        questions,
        MarkingScheme(correct=3, wrong=-2, skip=-0.5),
    )

    assert result.score == 0.5


@pytest.mark.parametrize(
    ("confidence", "selected_key", "expected_correct", "expected_wrong"),
    [
        (Confidence.SURE, "A", 1, 0),
        (Confidence.SURE, "B", 0, 1),
        (Confidence.NOT_SURE, "A", 1, 0),
        (Confidence.NOT_SURE, "B", 0, 1),
        (Confidence.GUESSING, "A", 1, 0),
        (Confidence.GUESSING, "B", 0, 1),
        (Confidence.UNRATED, "A", 1, 0),
        (Confidence.UNRATED, "B", 0, 1),
    ],
)
def test_confidence_bucket_analytics(
    confidence: Confidence,
    selected_key: str,
    expected_correct: int,
    expected_wrong: int,
) -> None:
    result = score_attempt(
        [_response("q1", selected_key, confidence)],
        {"q1": _question("q1", 1)},
        MarkingScheme(),
    )

    assert result.confidence_totals[confidence] == 1
    assert result.confidence_correct[confidence] == expected_correct
    assert result.confidence_wrong[confidence] == expected_wrong


def test_skipped_response_is_excluded_from_confidence_buckets() -> None:
    result = score_attempt(
        [_response("q1", None, None)],
        {"q1": _question("q1", 1)},
        MarkingScheme(),
    )

    assert sum(result.confidence_totals.values()) == 0


def test_unknown_question_reference_is_rejected() -> None:
    response = _response("missing", "A", Confidence.SURE)

    with pytest.raises(ValueError, match="Unknown question_id 'missing'"):
        score_attempt([response], {"q1": _question("q1", 1)}, MarkingScheme())


def test_duplicate_current_response_is_rejected() -> None:
    responses = [
        _response("q1", "A", Confidence.SURE, response_id="response-1"),
        _response("q1", "B", Confidence.NOT_SURE, response_id="response-2"),
    ]

    with pytest.raises(ValueError, match="Duplicate response for question 'q1'"):
        score_attempt(responses, {"q1": _question("q1", 1)}, MarkingScheme())


def test_insight_ids_use_position_then_id_order() -> None:
    questions = {
        "q-z": _question("q-z", 2, "A"),
        "q-b": _question("q-b", 1, "B"),
        "q-a": _question("q-a", 1, "A"),
    }
    responses = [
        _response("q-z", "B", Confidence.SURE),
        _response("q-b", "B", Confidence.GUESSING),
        _response("q-a", "C", Confidence.SURE),
    ]

    result = score_attempt(responses, questions, MarkingScheme())

    assert result.sure_but_wrong_question_ids == ("q-a", "q-z")
    assert result.guessed_right_question_ids == ("q-b",)

