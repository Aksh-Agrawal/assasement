"""Focused tests for Phase 2 domain models."""

from datetime import UTC, datetime

import pytest

from app.core.models import (
    Attempt,
    AttemptStatus,
    Confidence,
    MarkingScheme,
    Option,
    Profile,
    Question,
    QuestionSet,
    Response,
    ScoreResult,
)


def _options() -> tuple[Option, ...]:
    return tuple(Option(key=key, text=f"Option {key}") for key in ("A", "B", "C", "D"))


def _question() -> Question:
    return Question(
        id="bio-cell-q0001",
        position=1,
        topic="Cell Organelles",
        difficulty=1,
        question_text="Which option is correct?",
        options=_options(),
        correct_key="A",
        explanation="A test explanation.",
        media_ref=None,
    )


def _zero_confidence_counts() -> dict[Confidence, int]:
    return dict.fromkeys(Confidence, 0)


def test_confidence_values_match_phase_zero_contract() -> None:
    assert {confidence.name: confidence.value for confidence in Confidence} == {
        "SURE": "sure",
        "NOT_SURE": "not_sure",
        "GUESSING": "guessing",
        "UNRATED": "unrated",
    }


def test_marking_scheme_defaults_and_custom_values() -> None:
    assert MarkingScheme() == MarkingScheme(correct=4, wrong=-1, skip=0)
    assert MarkingScheme(correct=3, wrong=-2, skip=-0.5).skip == -0.5


def test_option_and_question_construction() -> None:
    question = _question()

    assert question.options[0] == Option(key="A", text="Option A")
    assert question.correct_key == "A"


def test_question_rejects_noncanonical_options() -> None:
    options = list(_options())
    options[0], options[1] = options[1], options[0]

    with pytest.raises(ValueError, match="ordered A, B, C, D"):
        Question(
            id="q1",
            position=1,
            topic="Topic",
            difficulty=1,
            question_text="Question",
            options=tuple(options),
            correct_key="A",
        )


def test_question_set_and_profile_construction() -> None:
    question_set = QuestionSet(
        id="biology-cell-practice-01",
        version=1,
        title="Cell Practice 1",
        subject="Biology",
        chapter="Cell: The Unit of Life",
        marking=MarkingScheme(),
        questions=(_question(),),
    )
    profile = Profile(id="550e8400-e29b-41d4-a716-446655440000", display_name="Student")

    assert question_set.questions[0].id == "bio-cell-q0001"
    assert profile.display_name == "Student"


def test_skipped_response_has_no_confidence() -> None:
    response = Response(id="response-1", attempt_id="attempt-1", question_id="q1")

    assert response.selected_key is None
    assert response.confidence is None


def test_answered_response_can_be_unrated() -> None:
    response = Response(
        id="response-1",
        attempt_id="attempt-1",
        question_id="q1",
        selected_key="B",
        confidence=Confidence.UNRATED,
    )

    assert response.selected_key == "B"
    assert response.confidence is Confidence.UNRATED


def test_response_rejects_confidence_for_skipped_answer() -> None:
    with pytest.raises(ValueError, match="skipped response cannot have confidence"):
        Response(
            id="response-1",
            attempt_id="attempt-1",
            question_id="q1",
            confidence=Confidence.SURE,
        )


def test_response_rejects_answer_without_stored_confidence() -> None:
    with pytest.raises(ValueError, match="must store confidence"):
        Response(
            id="response-1",
            attempt_id="attempt-1",
            question_id="q1",
            selected_key="A",
        )


def test_response_rejects_unparsed_confidence_string() -> None:
    with pytest.raises(ValueError, match="must be a Confidence value"):
        Response(
            id="response-1",
            attempt_id="attempt-1",
            question_id="q1",
            selected_key="A",
            confidence="sure",  # type: ignore[arg-type]
        )


def test_attempt_construction_has_no_persistence_behavior() -> None:
    attempt = Attempt(
        id="attempt-1",
        profile_id="profile-1",
        set_id="biology-cell-practice-01",
        set_version=1,
        status=AttemptStatus.IN_PROGRESS,
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    assert attempt.duration_ms == 0
    assert attempt.score is None


def test_score_result_construction_freezes_confidence_mappings() -> None:
    totals = _zero_confidence_counts()
    result = ScoreResult(
        score=0,
        correct=0,
        wrong=0,
        skipped=1,
        attempted=0,
        accuracy=0.0,
        confidence_totals=totals,
        confidence_correct=_zero_confidence_counts(),
        confidence_wrong=_zero_confidence_counts(),
        sure_but_wrong_question_ids=(),
        guessed_right_question_ids=(),
    )
    totals[Confidence.SURE] = 99

    assert result.confidence_totals[Confidence.SURE] == 0
    with pytest.raises(TypeError):
        result.confidence_totals[Confidence.SURE] = 1  # type: ignore[index]

