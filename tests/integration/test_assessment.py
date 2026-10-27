"""SQLite-backed tests for the complete offline assessment vertical slice."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.assessment import AssessmentApplication
from app.core.engine import AssessmentState
from app.core.models import (
    AttemptStatus,
    Confidence,
    MarkingScheme,
    Option,
    Profile,
    Question,
    QuestionSet,
)
from app.core.scoring import score_attempt
from app.data.repo import Repository, SyncStatus

PROFILE = Profile(id="550e8400-e29b-41d4-a716-446655440000", display_name="Student")


class FakeClock:
    def __init__(self, value: float = 10.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class IdFactory:
    def __init__(self) -> None:
        self.number = 0

    def __call__(self) -> str:
        self.number += 1
        return f"00000000-0000-4000-8000-{self.number:012d}"


def make_question_set(version: int = 1) -> QuestionSet:
    options = tuple(Option(key=key, text=f"Option {key}") for key in ("A", "B", "C", "D"))
    keys = ("A", "B", "C", "D")
    questions = tuple(
        Question(
            id=f"bio-phase4-q{position:04d}",
            position=position,
            topic="Phase 4",
            difficulty=(position % 3) + 1,
            question_text=f"Development question {position}, version {version}",
            options=options,
            correct_key=keys[(position - 1) % 4],  # type: ignore[arg-type]
            explanation=f"Development explanation {position}.",
        )
        for position in range(1, 21)
    )
    return QuestionSet(
        id="biology-phase4-test-01",
        version=version,
        title=f"Phase 4 Test v{version}",
        subject="Biology",
        chapter="Development Fixtures",
        marking=MarkingScheme(),
        questions=questions,
    )


def seed(repository: Repository, *, version: int = 1, active: bool = True) -> QuestionSet:
    question_set = make_question_set(version)
    if repository.get_profile(PROFILE.id) is None:
        repository.create_profile(PROFILE, created_at=datetime(2026, 1, 1, tzinfo=UTC))
    repository.import_question_set(
        question_set,
        content_hash=f"sha256:phase4-v{version}",
        downloaded_at=datetime(2026, 1, version, tzinfo=UTC),
        is_active=active,
    )
    return question_set


def make_app(repository: Repository, clock: FakeClock, ids: IdFactory) -> AssessmentApplication:
    wall_time = datetime(2026, 2, 1, tzinfo=UTC)
    return AssessmentApplication(
        repository,
        monotonic_clock=clock,
        wall_clock=lambda: wall_time + timedelta(seconds=clock.value),
        id_factory=ids,
    )


def test_full_twenty_question_assessment_uses_repository_and_phase2_scoring(
    tmp_path: Path,
) -> None:
    clock = FakeClock()
    ids = IdFactory()
    with Repository(tmp_path / "full.db") as repository:
        question_set = seed(repository)
        app = make_app(repository, clock, ids)
        attempt = app.start_test(PROFILE.id, question_set.id, 1, shuffle_seed=74)
        persisted_order = repository.get_attempt_question_order(attempt.id)
        assert persisted_order != tuple(question.id for question in question_set.questions)

        confidence_cycle = (
            Confidence.SURE,
            Confidence.NOT_SURE,
            Confidence.GUESSING,
            Confidence.UNRATED,
        )
        for index in range(20):
            clock.advance(index + 1)
            question = app.current_question()
            app.select_answer(question.correct_key if index % 3 else "D")
            confidence = confidence_cycle[index % len(confidence_cycle)]
            if confidence is Confidence.UNRATED:
                app.continue_unrated()
            else:
                app.set_confidence(confidence)
            if index < 19:
                app.next_question()

        app.go_to_question(0)
        first = app.current_question()
        replacement = "B" if first.correct_key != "B" else "C"
        app.select_answer(replacement)
        app.set_confidence(Confidence.SURE)
        app.set_marked_review(True)
        app.next_question()
        app.previous_question()
        assert app.current_response() is not None
        assert app.current_response().marked_review is True  # type: ignore[union-attr]

        app.request_submit()
        result = app.submit()
        expected = score_attempt(
            repository.get_attempt_responses(attempt.id),
            {question.id: question for question in question_set.questions},
            question_set.marking,
        )

        assert result == expected
        assert app.engine.state is AssessmentState.RESULT
        completed = repository.get_attempt(attempt.id)
        assert completed is not None
        assert completed.status is AttemptStatus.COMPLETED
        assert completed.score == expected.score
        assert completed.duration_ms == sum(
            response.response_time_ms
            for response in repository.get_attempt_responses(attempt.id)
        )
        assert repository.get_attempt_sync_state(attempt.id).status is SyncStatus.PENDING
        assert len(app.open_review()) == 20

        event_types = [event.event_type for event in repository.get_response_events(attempt.id)]
        assert "selected" in event_types
        assert "changed" in event_types
        assert "confidence_set" in event_types
        assert "review_marked" in event_types


def test_crash_restart_resume_restores_order_answers_flags_confidence_and_time(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "restart.db"
    ids = IdFactory()
    first_clock = FakeClock(100)
    with Repository(database_path) as repository:
        question_set = seed(repository)
        app = make_app(repository, first_clock, ids)
        attempt = app.start_test(PROFILE.id, question_set.id, 1, shuffle_seed=19)
        original_order = repository.get_attempt_question_order(attempt.id)

        expected_answers: dict[str, tuple[str, Confidence]] = {}
        for index in range(7):
            first_clock.advance(index + 0.5)
            question = app.current_question()
            confidence = (Confidence.SURE, Confidence.NOT_SURE, Confidence.GUESSING)[index % 3]
            app.select_answer(question.correct_key)
            app.set_confidence(confidence)
            expected_answers[question.id] = (question.correct_key, confidence)
            if index == 2:
                app.set_marked_review(True)
            app.next_question()
        persisted_before_restart = {
            response.question_id: response for response in repository.get_attempt_responses(attempt.id)
        }
        assert sum(
            response.response_time_ms for response in persisted_before_restart.values()
        ) > 0

    second_clock = FakeClock(10_000)
    with Repository(database_path) as repository:
        app = make_app(repository, second_clock, ids)
        resumed = app.resume_attempt(PROFILE.id)
        assert resumed is not None and resumed.id == attempt.id
        assert app.engine.ordered_question_ids == original_order
        assert app.current_question().id == original_order[7]

        restored = {
            response.question_id: response for response in repository.get_attempt_responses(attempt.id)
        }
        for question_id, (answer, confidence) in expected_answers.items():
            assert restored[question_id].selected_key == answer
            assert restored[question_id].confidence is confidence
            assert restored[question_id].response_time_ms == persisted_before_restart[
                question_id
            ].response_time_ms
        assert restored[original_order[2]].marked_review is True

        for index in range(7, 20):
            second_clock.advance(1)
            app.select_answer(app.current_question().correct_key)
            app.continue_unrated()
            if index < 19:
                app.next_question()

        app.go_to_question(0)
        changed_question = app.current_question()
        wrong_key = "D" if changed_question.correct_key != "D" else "A"
        app.select_answer(wrong_key)
        app.set_confidence(Confidence.SURE)
        app.request_submit()
        result = app.submit()
        expected = score_attempt(
            repository.get_attempt_responses(attempt.id),
            {question.id: question for question in question_set.questions},
            question_set.marking,
        )
        assert result == expected
        completed = repository.get_attempt(attempt.id)
        assert completed is not None
        assert completed.status is AttemptStatus.COMPLETED


def test_answer_is_committed_before_confidence_or_safe_exit(tmp_path: Path) -> None:
    database_path = tmp_path / "immediate.db"
    ids = IdFactory()
    with Repository(database_path) as repository:
        question_set = seed(repository)
        app = make_app(repository, FakeClock(), ids)
        attempt = app.start_test(PROFILE.id, question_set.id, 1)
        question_id = app.current_question().id
        app.select_answer("B")
        stored = repository.get_response(attempt.id, question_id)
        assert stored is not None
        assert stored.selected_key == "B"
        assert stored.confidence is Confidence.UNRATED

    with Repository(database_path) as repository:
        stored = repository.get_response(attempt.id, question_id)
        assert stored is not None
        assert stored.selected_key == "B"
        assert stored.confidence is Confidence.UNRATED


def test_in_progress_attempt_remains_on_original_set_version(tmp_path: Path) -> None:
    database_path = tmp_path / "versions.db"
    ids = IdFactory()
    with Repository(database_path) as repository:
        version_1 = seed(repository)
        app = make_app(repository, FakeClock(), ids)
        attempt = app.start_test(PROFILE.id, version_1.id, 1, shuffle_seed=5)
        order = repository.get_attempt_question_order(attempt.id)
        seed(repository, version=2, active=False)
        repository.set_active_question_set(version_1.id, 2)

    with Repository(database_path) as repository:
        app = make_app(repository, FakeClock(500), ids)
        resumed = app.resume_attempt(PROFILE.id)
        assert resumed is not None
        assert resumed.set_version == 1
        assert app.engine.question_set is not None
        assert app.engine.question_set.version == 1
        assert app.engine.ordered_question_ids == order
