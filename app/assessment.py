"""Application orchestration joining pure engine, repository, timing, and scoring."""

import logging
import random
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from app.core.engine import AssessmentEngine, AssessmentState, ReviewItem
from app.core.models import (
    Attempt,
    AttemptStatus,
    Confidence,
    OptionKey,
    Question,
    Response,
    ScoreResult,
)
from app.core.scoring import score_attempt
from app.core.timer import MonotonicTimer
from app.data.repo import Repository

LOGGER = logging.getLogger(__name__)


class AssessmentApplication:
    """Small offline application service; all durable state goes through Repository."""

    def __init__(
        self,
        repository: Repository,
        *,
        monotonic_clock: Callable[[], float] | None = None,
        wall_clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.repository = repository
        self.engine = AssessmentEngine()
        self._monotonic_clock = monotonic_clock
        self._wall_clock = wall_clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._timer: MonotonicTimer | None = None

    def start_test(
        self,
        profile_id: str,
        set_id: str,
        version: int,
        *,
        shuffle_seed: int | None = None,
        institute_assignment_id: str | None = None,
    ) -> Attempt:
        """Create and persist a new attempt with an authoritative fixed order."""
        self.repository.reconcile_content_state(profile_id)
        if self.repository.find_in_progress_attempt(profile_id) is not None:
            raise RuntimeError("Profile already has an in-progress attempt")
        allowed = self.repository.can_start_pack(profile_id, set_id, version)
        if institute_assignment_id:
            allowed = any(a["assignment_id"] == institute_assignment_id and a["set_id"] == set_id
                and a["version"] == version for a in self.repository.institute_work(profile_id))
        if not allowed:
            raise ValueError("This pack is not available for the selected profile")
        question_set = self.repository.get_question_set(set_id, version)
        if question_set is None:
            raise ValueError(f"Unknown question set {set_id!r} version {version}")
        ordered_ids = [question.id for question in question_set.questions]
        if shuffle_seed is not None:
            random.Random(shuffle_seed).shuffle(ordered_ids)
        attempt = Attempt(
            id=self._id_factory(),
            profile_id=profile_id,
            set_id=set_id,
            set_version=version,
            status=AttemptStatus.IN_PROGRESS,
            started_at=self._now(),
        )
        self.repository.create_attempt(attempt, question_order=ordered_ids,
            institute_assignment_id=institute_assignment_id)
        self.engine = AssessmentEngine()
        self._timer = None
        self.engine.select_test(question_set)
        self.engine.start_test(attempt, tuple(ordered_ids))
        self._activate_current_question()
        LOGGER.info("attempt resumed attempt_id=%s", attempt.id)
        return attempt

    def resume_attempt(self, profile_id: str) -> Attempt | None:
        """Resume the profile's in-progress attempt from durable state."""
        self.repository.reconcile_content_state(profile_id)
        attempt = self.repository.find_in_progress_attempt(profile_id)
        if attempt is None:
            self.engine = AssessmentEngine()
            self._timer = None
            return None
        question_set = self.repository.get_question_set(attempt.set_id, attempt.set_version)
        if question_set is None:
            raise RuntimeError("Attempt question-set version is not installed")
        order = self.repository.get_attempt_question_order(attempt.id)
        if self.engine.attempt and self.engine.attempt.id == attempt.id:
            self.pause()
        responses = self.repository.get_attempt_responses(attempt.id)
        engine = AssessmentEngine()
        engine.resume_attempt(attempt, question_set, order, responses)
        self.engine = engine
        self._timer = None
        self._activate_current_question()
        return attempt

    def reconcile_session(self) -> bool:
        """Drop an in-memory pointer only when its durable session stopped being active."""
        attempt = self.engine.attempt
        if attempt is None:
            return False
        stored = self.repository.get_attempt(attempt.id)
        if stored is not None and stored.status != AttemptStatus.ABANDONED:
            return False
        if attempt.status != AttemptStatus.IN_PROGRESS:
            return False
        self.engine = AssessmentEngine()
        self._timer = None
        LOGGER.info("cleared resume pointer attempt_id=%s", attempt.id)
        return True

    def current_question(self) -> Question:
        return self.engine.current_question()

    def current_response(self) -> Response | None:
        return self.engine.current_response()

    def current_time_ms(self) -> int:
        """Return persisted plus current active time for display."""
        if self._timer is None:
            response = self.engine.current_response()
            return response.response_time_ms if response else 0
        return self._timer.elapsed_ms

    def select_answer(self, key: OptionKey) -> Response:
        """Persist an answer immediately, then await explicit confidence."""
        existing = self.engine.current_response()
        previous_key = existing.selected_key if existing else None
        elapsed = self._pause_timer()
        response = self.engine.select_answer(
            key,
            response_time_ms=elapsed,
            response_id=self._id_factory(),
        )
        question = self.engine.current_question()
        stored = self.repository.save_response(
            response,
            is_correct=key == question.correct_key,
            answered_at=self._now(),
        )
        self.engine.update_current_response(stored)
        event_type = "changed" if previous_key is not None and previous_key != key else "selected"
        self._append_event(event_type, key, elapsed)
        self._resume_timer(elapsed)
        return stored

    def set_confidence(self, confidence: Confidence) -> Response:
        """Persist explicit confidence on the same current response row."""
        elapsed = self._pause_timer()
        response = self.engine.set_confidence(confidence)
        response = replace(response, response_time_ms=elapsed)
        self.engine.update_current_response(response)
        question = self.engine.current_question()
        stored = self.repository.save_response(
            response,
            is_correct=response.selected_key == question.correct_key,
        )
        self.engine.update_current_response(stored)
        self._append_event("confidence_set", confidence.value, elapsed)
        self._resume_timer(elapsed)
        return stored

    def continue_unrated(self) -> Response:
        """Persist and accept the existing unrated confidence choice."""
        elapsed = self._pause_timer()
        response = replace(self.engine.continue_unrated(), response_time_ms=elapsed)
        self.engine.update_current_response(response)
        question = self.engine.current_question()
        stored = self.repository.save_response(
            response,
            is_correct=response.selected_key == question.correct_key,
        )
        self.engine.update_current_response(stored)
        self._append_event("confidence_set", Confidence.UNRATED.value, elapsed)
        self._resume_timer(elapsed)
        return stored

    def next_question(self) -> Question | None:
        self._pause_and_persist_current()
        question = self.engine.next_question()
        if question is not None:
            self._activate_current_question()
        return question

    def previous_question(self) -> Question:
        self._pause_and_persist_current()
        question = self.engine.previous_question()
        self._activate_current_question()
        return question

    def go_to_question(self, index: int) -> Question:
        self._pause_and_persist_current()
        question = self.engine.go_to_question(index)
        self._activate_current_question()
        return question

    def set_marked_review(self, marked: bool) -> Response:
        elapsed = self._pause_timer()
        response = self.engine.mark_for_review(
            marked,
            response_id=self._id_factory(),
            response_time_ms=elapsed,
        )
        is_correct = self._correctness(response)
        stored = self.repository.save_response(response, is_correct=is_correct)
        self.engine.update_current_response(stored)
        self._append_event("review_marked" if marked else "review_unmarked", None, elapsed)
        self._resume_timer(elapsed)
        return stored

    def request_submit(self) -> None:
        self._pause_and_persist_current()
        self.engine.request_submit()

    def cancel_submit(self) -> None:
        self.engine.cancel_submit()
        self._activate_current_question()

    def submit(self) -> ScoreResult:
        """Score once, atomically complete persistence, and display the result."""
        if self.engine.state is not AssessmentState.SUBMIT_CONFIRM:
            raise RuntimeError("Submission must be explicitly requested first")
        attempt = self.engine.attempt
        question_set = self.engine.question_set
        if attempt is None or question_set is None:
            raise RuntimeError("No active attempt")
        responses = self.repository.get_attempt_responses(attempt.id)
        questions_by_id = {question.id: question for question in question_set.questions}
        result = score_attempt(responses, questions_by_id, question_set.marking)
        duration_ms = sum(response.response_time_ms for response in responses)
        self.repository.complete_attempt(
            attempt.id,
            completed_at=self._now(),
            duration_ms=duration_ms,
            score=result.score,
        )
        LOGGER.info("attempt completed attempt_id=%s", attempt.id)
        self.engine.confirm_submission(result)
        return self.engine.show_result()

    def pause(self) -> None:
        """Persist accumulated timing before menu display or safe process exit."""
        if self.reconcile_session():
            return
        if self.engine.state in {
            AssessmentState.IN_QUESTION,
            AssessmentState.AWAITING_CONFIDENCE,
        }:
            self._pause_and_persist_current()

    def abandon(self) -> None:
        """Explicitly abandon without deleting durable history."""
        self.pause()
        attempt = self.engine.attempt
        if attempt is None:
            raise RuntimeError("No active attempt")
        self.repository.mark_attempt_abandoned(attempt.id, completed_at=self._now())
        self.engine.abandon()

    def open_review(self) -> tuple[ReviewItem, ...]:
        return self.engine.open_review()

    def close_review(self) -> None:
        self.engine.close_review()

    def _activate_current_question(self) -> None:
        response = self.engine.current_response()
        if response is None:
            response = self.engine.ensure_current_response(response_id=self._id_factory())
            stored = self.repository.save_response(
                response,
                is_correct=None,
                first_shown_at=self._now(),
            )
            self.engine.update_current_response(stored)
            response = stored
        self._resume_timer(response.response_time_ms)

    def _pause_timer(self) -> int:
        if self._timer is None:
            response = self.engine.current_response()
            return response.response_time_ms if response else 0
        elapsed = self._timer.pause()
        self._timer = None
        return elapsed

    def _resume_timer(self, initial_ms: int) -> None:
        clock_options = {} if self._monotonic_clock is None else {"clock": self._monotonic_clock}
        self._timer = MonotonicTimer(initial_ms=initial_ms, **clock_options)
        self._timer.start()

    def _pause_and_persist_current(self) -> Response:
        elapsed = self._pause_timer()
        response = self.engine.ensure_current_response(
            response_id=self._id_factory(), response_time_ms=elapsed
        )
        response = replace(response, response_time_ms=elapsed)
        self.engine.update_current_response(response)
        stored = self.repository.save_response(response, is_correct=self._correctness(response))
        self.engine.update_current_response(stored)
        return stored

    def _correctness(self, response: Response) -> bool | None:
        if response.selected_key is None:
            return None
        return response.selected_key == self.engine.current_question().correct_key

    def _append_event(
        self, event_type: str, value: str | None, at_ms: int
    ) -> None:
        attempt = self.engine.attempt
        if attempt is None:
            raise RuntimeError("No active attempt")
        self.repository.append_response_event(
            event_id=self._id_factory(),
            attempt_id=attempt.id,
            question_id=self.engine.current_question().id,
            event_type=event_type,
            value=value,
            at_ms=at_ms,
            at_utc=self._now(),
        )

    def _now(self) -> datetime:
        value = self._wall_clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Wall clock must return a timezone-aware datetime")
        return value
