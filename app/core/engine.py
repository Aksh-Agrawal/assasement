"""Pure assessment state machine independent of persistence and hardware."""

from dataclasses import dataclass, replace
from enum import StrEnum
from uuid import uuid4

from app.core.models import (
    Attempt,
    Confidence,
    OptionKey,
    Question,
    QuestionSet,
    Response,
    ScoreResult,
)


class AssessmentState(StrEnum):
    """Approved Phase 0 assessment states."""

    IDLE = "IDLE"
    TEST_SELECTED = "TEST_SELECTED"
    IN_QUESTION = "IN_QUESTION"
    AWAITING_CONFIDENCE = "AWAITING_CONFIDENCE"
    SUBMIT_CONFIRM = "SUBMIT_CONFIRM"
    COMPLETED = "COMPLETED"
    RESULT = "RESULT"
    REVIEW = "REVIEW"


class InvalidTransition(RuntimeError):
    """Raised when an action is invalid in the current assessment state."""


class NavigationBoundary(InvalidTransition):
    """Raised when navigation would move outside the assessment."""


@dataclass(frozen=True, slots=True)
class ReviewItem:
    """One immutable question/response view for completed review."""

    position: int
    question: Question
    response: Response | None

    @property
    def outcome(self) -> str:
        if self.response is None or self.response.selected_key is None:
            return "skipped"
        if self.response.selected_key == self.question.correct_key:
            return "correct"
        return "wrong"


class AssessmentEngine:
    """Pure in-memory state machine; durable writes are orchestrated externally."""

    def __init__(self) -> None:
        self.state = AssessmentState.IDLE
        self.attempt: Attempt | None = None
        self.question_set: QuestionSet | None = None
        self.ordered_question_ids: tuple[str, ...] = ()
        self.current_index = 0
        self._questions_by_id: dict[str, Question] = {}
        self._responses: dict[str, Response] = {}
        self._result: ScoreResult | None = None

    def _require_state(self, *allowed: AssessmentState) -> None:
        if self.state not in allowed:
            names = ", ".join(state.value for state in allowed)
            raise InvalidTransition(f"State {self.state.value} requires one of: {names}")

    def select_test(self, question_set: QuestionSet) -> None:
        """Select an exact immutable question-set version."""
        self._require_state(AssessmentState.IDLE)
        self.question_set = question_set
        self._questions_by_id = {question.id: question for question in question_set.questions}
        self.state = AssessmentState.TEST_SELECTED

    def start_test(self, attempt: Attempt, ordered_question_ids: tuple[str, ...]) -> None:
        """Start a selected test with a caller-persisted attempt and order."""
        self._require_state(AssessmentState.TEST_SELECTED)
        self._validate_attempt_and_order(attempt, ordered_question_ids)
        self.attempt = attempt
        self.ordered_question_ids = tuple(ordered_question_ids)
        self.current_index = 0
        self._responses = {}
        self.state = AssessmentState.IN_QUESTION

    def resume_attempt(
        self,
        attempt: Attempt,
        question_set: QuestionSet,
        ordered_question_ids: tuple[str, ...],
        responses: tuple[Response, ...],
    ) -> None:
        """Restore persisted state and choose the first unanswered question."""
        self._require_state(AssessmentState.IDLE)
        self.question_set = question_set
        self._questions_by_id = {question.id: question for question in question_set.questions}
        self._validate_attempt_and_order(attempt, ordered_question_ids)
        response_map = {response.question_id: response for response in responses}
        if len(response_map) != len(responses):
            raise ValueError("Resume responses contain duplicate question IDs")
        unknown = set(response_map) - set(ordered_question_ids)
        if unknown:
            raise ValueError(f"Resume responses reference unknown questions: {sorted(unknown)!r}")
        self.attempt = attempt
        self.ordered_question_ids = tuple(ordered_question_ids)
        self._responses = response_map
        self.current_index = self._resume_index()
        self.state = AssessmentState.IN_QUESTION

    def _validate_attempt_and_order(
        self, attempt: Attempt, ordered_question_ids: tuple[str, ...]
    ) -> None:
        if self.question_set is None:
            raise InvalidTransition("No question set is selected")
        if (attempt.set_id, attempt.set_version) != (
            self.question_set.id,
            self.question_set.version,
        ):
            raise ValueError("Attempt does not reference the selected question-set version")
        if len(ordered_question_ids) != len(set(ordered_question_ids)):
            raise ValueError("Question order contains duplicates")
        if set(ordered_question_ids) != set(self._questions_by_id):
            raise ValueError("Question order must contain every selected-set question exactly once")

    def _resume_index(self) -> int:
        for index, question_id in enumerate(self.ordered_question_ids):
            response = self._responses.get(question_id)
            if response is None or response.selected_key is None:
                return index
        return max(0, len(self.ordered_question_ids) - 1)

    def current_question(self) -> Question:
        """Return the active question in interactive question states."""
        self._require_state(
            AssessmentState.IN_QUESTION,
            AssessmentState.AWAITING_CONFIDENCE,
            AssessmentState.SUBMIT_CONFIRM,
        )
        return self._questions_by_id[self.ordered_question_ids[self.current_index]]

    def current_response(self) -> Response | None:
        """Return current persisted-style response state, if one exists."""
        question = self.current_question()
        return self._responses.get(question.id)

    def ensure_current_response(
        self, *, response_id: str | None = None, response_time_ms: int = 0
    ) -> Response:
        """Create an unanswered current response when timing/review must persist."""
        self._require_state(AssessmentState.IN_QUESTION, AssessmentState.AWAITING_CONFIDENCE)
        existing = self.current_response()
        if existing is not None:
            return existing
        if self.attempt is None:
            raise InvalidTransition("No active attempt")
        response = Response(
            id=response_id or str(uuid4()),
            attempt_id=self.attempt.id,
            question_id=self.current_question().id,
            response_time_ms=response_time_ms,
        )
        self._responses[response.question_id] = response
        return response

    def update_current_response(self, response: Response) -> None:
        """Replace in-memory current state with a durably mapped response."""
        self._require_state(AssessmentState.IN_QUESTION, AssessmentState.AWAITING_CONFIDENCE)
        if response.question_id != self.current_question().id:
            raise ValueError("Response is not for the current question")
        self._responses[response.question_id] = response

    def select_answer(
        self,
        key: OptionKey,
        *,
        response_time_ms: int,
        response_id: str | None = None,
    ) -> Response:
        """Select/change an answer and represent pending confidence as unrated."""
        self._require_state(AssessmentState.IN_QUESTION)
        existing = self.current_response()
        if self.attempt is None:
            raise InvalidTransition("No active attempt")
        response = Response(
            id=existing.id if existing else (response_id or str(uuid4())),
            attempt_id=self.attempt.id,
            question_id=self.current_question().id,
            selected_key=key,
            confidence=Confidence.UNRATED,
            response_time_ms=response_time_ms,
            marked_review=existing.marked_review if existing else False,
        )
        self._responses[response.question_id] = response
        self.state = AssessmentState.AWAITING_CONFIDENCE
        return response

    def set_confidence(self, confidence: Confidence) -> Response:
        """Set explicit confidence and return to normal question interaction."""
        self._require_state(AssessmentState.AWAITING_CONFIDENCE)
        if confidence is Confidence.UNRATED:
            raise ValueError("Use continue_unrated for an unrated answer")
        response = self.current_response()
        if response is None or response.selected_key is None:
            raise InvalidTransition("Confidence requires a selected answer")
        updated = replace(response, confidence=confidence)
        self._responses[updated.question_id] = updated
        self.state = AssessmentState.IN_QUESTION
        return updated

    def continue_unrated(self) -> Response:
        """Accept the already persisted unrated confidence value."""
        self._require_state(AssessmentState.AWAITING_CONFIDENCE)
        response = self.current_response()
        if response is None or response.selected_key is None:
            raise InvalidTransition("Unrated continuation requires a selected answer")
        self.state = AssessmentState.IN_QUESTION
        return response

    def mark_for_review(
        self,
        marked: bool,
        *,
        response_id: str | None = None,
        response_time_ms: int | None = None,
    ) -> Response:
        """Set or clear the current review marker in memory."""
        self._require_state(AssessmentState.IN_QUESTION, AssessmentState.AWAITING_CONFIDENCE)
        response = self.ensure_current_response(
            response_id=response_id,
            response_time_ms=response_time_ms or 0,
        )
        updated = replace(
            response,
            marked_review=marked,
            response_time_ms=(
                response.response_time_ms if response_time_ms is None else response_time_ms
            ),
        )
        self._responses[updated.question_id] = updated
        return updated

    def next_question(self) -> Question | None:
        """Advance, or enter submit confirmation after the final question."""
        self._require_state(AssessmentState.IN_QUESTION)
        if self.current_index == len(self.ordered_question_ids) - 1:
            self.state = AssessmentState.SUBMIT_CONFIRM
            return None
        self.current_index += 1
        return self.current_question()

    def previous_question(self) -> Question:
        """Move backward without wrapping."""
        self._require_state(AssessmentState.IN_QUESTION)
        if self.current_index == 0:
            raise NavigationBoundary("Already at the first question")
        self.current_index -= 1
        return self.current_question()

    def go_to_question(self, index: int) -> Question:
        """Move to a zero-based question index."""
        self._require_state(AssessmentState.IN_QUESTION)
        if not 0 <= index < len(self.ordered_question_ids):
            raise NavigationBoundary(f"Question index {index} is outside the assessment")
        self.current_index = index
        return self.current_question()

    def request_submit(self) -> None:
        """Enter explicit submission confirmation."""
        self._require_state(AssessmentState.IN_QUESTION)
        self.state = AssessmentState.SUBMIT_CONFIRM

    def cancel_submit(self) -> None:
        """Return from confirmation to the previously active question."""
        self._require_state(AssessmentState.SUBMIT_CONFIRM)
        self.state = AssessmentState.IN_QUESTION

    def confirm_submission(self, result: ScoreResult) -> None:
        """Record a durably completed result after repository completion succeeds."""
        self._require_state(AssessmentState.SUBMIT_CONFIRM)
        self._result = result
        self.state = AssessmentState.COMPLETED

    def show_result(self) -> ScoreResult:
        """Transition a completed attempt to result display."""
        self._require_state(AssessmentState.COMPLETED)
        if self._result is None:
            raise InvalidTransition("Completed assessment has no result")
        self.state = AssessmentState.RESULT
        return self._result

    def get_result(self) -> ScoreResult:
        """Return the completed result without recalculating it."""
        self._require_state(
            AssessmentState.COMPLETED,
            AssessmentState.RESULT,
            AssessmentState.REVIEW,
        )
        if self._result is None:
            raise InvalidTransition("No completed result is available")
        return self._result

    def open_review(self) -> tuple[ReviewItem, ...]:
        """Enter review and return every item in attempt order."""
        self._require_state(AssessmentState.RESULT)
        self.state = AssessmentState.REVIEW
        return self.review_items()

    def review_items(self) -> tuple[ReviewItem, ...]:
        """Return deterministic completed review items."""
        self._require_state(AssessmentState.REVIEW)
        return tuple(
            ReviewItem(
                position=index + 1,
                question=self._questions_by_id[question_id],
                response=self._responses.get(question_id),
            )
            for index, question_id in enumerate(self.ordered_question_ids)
        )

    def close_review(self) -> None:
        """Return from review to result display."""
        self._require_state(AssessmentState.REVIEW)
        self.state = AssessmentState.RESULT

    def responses(self) -> tuple[Response, ...]:
        """Return existing response objects in attempt order."""
        return tuple(
            self._responses[question_id]
            for question_id in self.ordered_question_ids
            if question_id in self._responses
        )

    def abandon(self) -> None:
        """Clear an explicitly abandoned active attempt from memory."""
        self._require_state(
            AssessmentState.IN_QUESTION,
            AssessmentState.AWAITING_CONFIDENCE,
            AssessmentState.SUBMIT_CONFIRM,
        )
        self.state = AssessmentState.IDLE
        self.attempt = None
        self.question_set = None
        self.ordered_question_ids = ()
        self._questions_by_id = {}
        self._responses = {}

