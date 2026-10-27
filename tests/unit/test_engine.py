"""Focused tests for the pure assessment state machine."""

from datetime import UTC, datetime

import pytest

from app.core.engine import (
    AssessmentEngine,
    AssessmentState,
    InvalidTransition,
    NavigationBoundary,
)
from app.core.models import (
    Attempt,
    Confidence,
    MarkingScheme,
    Option,
    Question,
    QuestionSet,
)
from app.core.scoring import score_attempt


def question_set() -> QuestionSet:
    options = tuple(Option(key=key, text=key) for key in ("A", "B", "C", "D"))
    questions = tuple(
        Question(
            id=f"q{position}",
            position=position,
            topic="Test",
            difficulty=1,
            question_text=f"Question {position}",
            options=options,
            correct_key=("A", "B", "C")[position - 1],  # type: ignore[arg-type]
        )
        for position in range(1, 4)
    )
    return QuestionSet(
        id="biology-test-01",
        version=1,
        title="Test",
        subject="Biology",
        chapter="Test",
        marking=MarkingScheme(),
        questions=questions,
    )


def attempt() -> Attempt:
    return Attempt(
        id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        profile_id="550e8400-e29b-41d4-a716-446655440000",
        set_id="biology-test-01",
        set_version=1,
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def started_engine() -> AssessmentEngine:
    engine = AssessmentEngine()
    engine.select_test(question_set())
    engine.start_test(attempt(), ("q1", "q2", "q3"))
    return engine


def test_full_state_transition_and_review_flow() -> None:
    engine = AssessmentEngine()
    assert engine.state is AssessmentState.IDLE

    selected_set = question_set()
    engine.select_test(selected_set)
    assert engine.state is AssessmentState.TEST_SELECTED
    engine.start_test(attempt(), ("q1", "q2", "q3"))
    assert engine.state is AssessmentState.IN_QUESTION
    assert engine.current_question().id == "q1"

    response = engine.select_answer("A", response_time_ms=500, response_id="r1")
    assert response.confidence is Confidence.UNRATED
    assert engine.state is AssessmentState.AWAITING_CONFIDENCE
    engine.set_confidence(Confidence.SURE)
    assert engine.state is AssessmentState.IN_QUESTION

    assert engine.next_question().id == "q2"  # type: ignore[union-attr]
    assert engine.previous_question().id == "q1"
    engine.go_to_question(2)
    assert engine.current_question().id == "q3"

    engine.request_submit()
    assert engine.state is AssessmentState.SUBMIT_CONFIRM
    engine.cancel_submit()
    assert engine.state is AssessmentState.IN_QUESTION
    engine.request_submit()

    result = score_attempt(
        engine.responses(),
        {question.id: question for question in selected_set.questions},
        selected_set.marking,
    )
    engine.confirm_submission(result)
    assert engine.state is AssessmentState.COMPLETED
    assert engine.show_result() == result
    items = engine.open_review()
    assert [item.outcome for item in items] == ["correct", "skipped", "skipped"]
    engine.close_review()
    assert engine.state is AssessmentState.RESULT


def test_invalid_transitions_and_navigation_boundaries_are_explicit() -> None:
    engine = AssessmentEngine()
    with pytest.raises(InvalidTransition):
        engine.request_submit()

    engine = started_engine()
    with pytest.raises(InvalidTransition):
        engine.set_confidence(Confidence.SURE)
    with pytest.raises(NavigationBoundary):
        engine.previous_question()
    with pytest.raises(NavigationBoundary):
        engine.go_to_question(99)


def test_final_next_enters_submit_confirmation_without_submitting() -> None:
    engine = started_engine()
    engine.go_to_question(2)
    assert engine.next_question() is None
    assert engine.state is AssessmentState.SUBMIT_CONFIRM


def test_resume_uses_first_unanswered_or_final_question() -> None:
    initial = started_engine()
    initial.select_answer("A", response_time_ms=100, response_id="r1")
    initial.continue_unrated()
    initial.next_question()
    initial.select_answer("B", response_time_ms=200, response_id="r2")
    initial.continue_unrated()

    resumed = AssessmentEngine()
    resumed.resume_attempt(
        attempt(), question_set(), ("q1", "q2", "q3"), initial.responses()
    )
    assert resumed.current_question().id == "q3"

    resumed.select_answer("C", response_time_ms=300, response_id="r3")
    resumed.continue_unrated()
    all_answered = AssessmentEngine()
    all_answered.resume_attempt(
        attempt(), question_set(), ("q1", "q2", "q3"), resumed.responses()
    )
    assert all_answered.current_question().id == "q3"
