"""End-to-end persistence tests for the SQLite repository."""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

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
)
from app.data.repo import (
    AttemptQuestionOrderAlreadyExists,
    DuplicateQuestionSetVersion,
    Repository,
    SyncStatus,
)

STARTED_AT = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
COMPLETED_AT = datetime(2026, 1, 2, 3, 14, 5, tzinfo=UTC)
PROFILE = Profile(id="550e8400-e29b-41d4-a716-446655440000", display_name="Student")


def _question(question_id: str, position: int, correct_key: str = "A") -> Question:
    options = tuple(
        Option(key=key, text=f"Option {key}") for key in ("A", "B", "C", "D")
    )
    return Question(
        id=question_id,
        position=position,
        topic="Persistence",
        difficulty=1,
        question_text=f"Question {question_id}",
        options=options,
        correct_key=correct_key,  # type: ignore[arg-type]
    )


def _question_set(version: int = 1) -> QuestionSet:
    ids = ("q5", "q2", "q8", "q1")
    questions = tuple(
        _question(question_id, position, ("A", "B", "C", "D")[position - 1])
        for position, question_id in enumerate(ids, start=1)
    )
    return QuestionSet(
        id="biology-cell-practice-01",
        version=version,
        title=f"Cell Practice {version}",
        subject="Biology",
        chapter="Cell: The Unit of Life",
        marking=MarkingScheme(),
        questions=questions,
    )


def _attempt(attempt_id: str = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa") -> Attempt:
    return Attempt(
        id=attempt_id,
        profile_id=PROFILE.id,
        set_id="biology-cell-practice-01",
        set_version=1,
        status=AttemptStatus.IN_PROGRESS,
        started_at=STARTED_AT,
    )


def _seed(repository: Repository) -> QuestionSet:
    question_set = _question_set()
    repository.create_profile(PROFILE, created_at=STARTED_AT)
    repository.import_question_set(
        question_set,
        content_hash="sha256:test-v1",
        downloaded_at=STARTED_AT,
        is_active=True,
    )
    return question_set


def test_profile_create_get_list_and_soft_delete(tmp_path: Path) -> None:
    with Repository(tmp_path / "profiles.db") as repository:
        repository.create_profile(PROFILE, created_at=STARTED_AT)

        assert repository.get_profile(PROFILE.id) == PROFILE
        assert repository.list_profiles() == (PROFILE,)
        assert repository.soft_delete_profile(PROFILE.id, deleted_at=COMPLETED_AT) is True
        assert repository.list_profiles() == ()
        assert repository.get_profile(PROFILE.id) == PROFILE


def test_question_set_versions_activation_order_and_duplicate_rejection(
    tmp_path: Path,
) -> None:
    with Repository(tmp_path / "sets.db") as repository:
        version_1 = _question_set(1)
        version_2 = _question_set(2)
        repository.import_question_set(version_1, content_hash="sha256:v1", is_active=True)
        repository.import_question_set(version_2, content_hash="sha256:v2")

        assert repository.list_question_set_versions(version_1.id) == (1, 2)
        assert repository.get_question_set(version_1.id, 1) == version_1
        assert repository.get_questions(version_1.id, 1) == version_1.questions
        assert repository.get_active_question_set(version_1.id) == version_1

        repository.set_active_question_set(version_1.id, 2)
        assert repository.get_active_question_set(version_1.id) == version_2

        with pytest.raises(DuplicateQuestionSetVersion):
            repository.import_question_set(version_1, content_hash="sha256:different")


def test_one_in_progress_attempt_per_profile_is_enforced(tmp_path: Path) -> None:
    with Repository(tmp_path / "attempt-invariant.db") as repository:
        _seed(repository)
        first = _attempt()
        repository.create_attempt(first)

        assert repository.find_in_progress_attempt(PROFILE.id) == first
        with pytest.raises(sqlite3.IntegrityError):
            repository.create_attempt(_attempt("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"))


def test_attempt_order_cannot_be_replaced(tmp_path: Path) -> None:
    with Repository(tmp_path / "fixed-order.db") as repository:
        _seed(repository)
        repository.create_attempt(_attempt(), question_order=("q5", "q2", "q8", "q1"))

        with pytest.raises(AttemptQuestionOrderAlreadyExists):
            repository.save_attempt_question_order(_attempt().id, ("q1", "q2"))


def test_response_update_preserves_id_and_event_is_independent(tmp_path: Path) -> None:
    with Repository(tmp_path / "response-update.db") as repository:
        _seed(repository)
        attempt = _attempt()
        repository.create_attempt(attempt, question_order=("q5",))
        initial = Response(
            id="response-original",
            attempt_id=attempt.id,
            question_id="q5",
            selected_key="A",
            confidence=Confidence.NOT_SURE,
            response_time_ms=100,
        )
        repository.save_response(initial, is_correct=True, answered_at=STARTED_AT)
        changed = Response(
            id="response-replacement-id",
            attempt_id=attempt.id,
            question_id="q5",
            selected_key="C",
            confidence=Confidence.SURE,
            response_time_ms=250,
        )

        stored = repository.save_response(changed, is_correct=False, answered_at=COMPLETED_AT)
        repository.append_response_event(
            event_id="event-1",
            attempt_id=attempt.id,
            question_id="q5",
            event_type="changed",
            value="C",
            at_ms=250,
            at_utc=COMPLETED_AT,
        )

        assert stored.id == "response-original"
        assert stored.selected_key == "C"
        assert len(repository.get_attempt_responses(attempt.id)) == 1
        assert repository.get_response_persistence(attempt.id, "q5").is_correct is False
        assert [event.event_type for event in repository.get_response_events(attempt.id)] == [
            "changed"
        ]


def test_complete_attempt_sets_pending_and_pending_query(tmp_path: Path) -> None:
    database_path = tmp_path / "complete.db"
    attempt = _attempt()
    with Repository(database_path) as repository:
        _seed(repository)
        repository.create_attempt(attempt, question_order=("q5",))
        completed = repository.complete_attempt(
            attempt.id,
            completed_at=COMPLETED_AT,
            duration_ms=600_000,
            score=4,
        )

        assert completed.status is AttemptStatus.COMPLETED
        assert completed.completed_at == COMPLETED_AT
        assert completed.duration_ms == 600_000
        assert completed.score == 4
        assert repository.get_attempt_sync_state(attempt.id).status is SyncStatus.PENDING
        assert repository.get_pending_attempts() == (completed,)

    with Repository(database_path) as repository:
        assert repository.get_attempt(attempt.id) == completed
        assert repository.get_attempt_sync_state(attempt.id).status is SyncStatus.PENDING


def test_settings_round_trip(tmp_path: Path) -> None:
    with Repository(tmp_path / "settings.db") as repository:
        repository.set_setting("theme", "high-contrast")
        assert repository.get_setting("theme") == "high-contrast"
        assert repository.delete_setting("theme") is True
        assert repository.get_setting("theme") is None


def test_full_attempt_state_survives_database_reopen(tmp_path: Path) -> None:
    database_path = tmp_path / "reopen.db"
    attempt = _attempt()
    order = ("q5", "q2", "q8", "q1")

    with Repository(database_path) as repository:
        _seed(repository)
        repository.create_attempt(attempt, question_order=order)
        repository.save_response(
            Response(
                id="response-q5",
                attempt_id=attempt.id,
                question_id="q5",
                selected_key="B",
                confidence=Confidence.SURE,
                response_time_ms=1_250,
                marked_review=True,
            ),
            is_correct=False,
            first_shown_at=STARTED_AT,
            answered_at=COMPLETED_AT,
        )
        repository.save_response(
            Response(
                id="response-q8",
                attempt_id=attempt.id,
                question_id="q8",
            ),
            is_correct=None,
            first_shown_at=STARTED_AT,
        )

    with Repository(database_path) as repository:
        loaded_attempt = repository.get_attempt(attempt.id)
        loaded_order = repository.get_attempt_question_order(attempt.id)
        loaded_responses = repository.get_attempt_responses(attempt.id)

        assert loaded_attempt == attempt
        assert loaded_order == order
        assert [response.question_id for response in loaded_responses] == ["q5", "q8"]
        assert loaded_responses[0].selected_key == "B"
        assert loaded_responses[0].confidence is Confidence.SURE
        assert loaded_responses[0].marked_review is True
        assert loaded_responses[1].selected_key is None
        repository.set_marked_review(attempt.id, "q5", False)

    with Repository(database_path) as repository:
        response = repository.get_response(attempt.id, "q5")
        assert response is not None
        assert response.marked_review is False
        assert response.selected_key == "B"
        assert response.confidence is Confidence.SURE
        assert repository.get_attempt_question_order(attempt.id) == order

