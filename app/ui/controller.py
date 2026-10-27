"""Framework-neutral UI routing over the real application and repository APIs."""

from collections.abc import Callable
from enum import StrEnum
from uuid import uuid4

from app.assessment import AssessmentApplication
from app.core.engine import NavigationBoundary, ReviewItem
from app.core.models import Confidence, Profile, QuestionSet, ScoreResult
from app.data.repo import Repository
from app.input.actions import Action


class UIScreen(StrEnum):
    PROFILE = "PROFILE"
    HOME = "PROFILE"  # Backward-compatible name for the root screen.
    SUBJECT = "SUBJECT"
    QUESTION_SET = "QUESTION_SET"
    QUESTION = "QUESTION"
    QUESTION_DETAIL = "QUESTION_DETAIL"
    CONFIDENCE = "CONFIDENCE"
    SUBMIT_CONFIRM = "SUBMIT_CONFIRM"
    RESULT = "RESULT"
    REVIEW = "REVIEW"
    ERROR = "ERROR"


class UIController:
    """Route canonical actions; assessment rules remain in the application service."""

    def __init__(
        self,
        repository: Repository,
        *,
        application_factory: Callable[[Repository], AssessmentApplication] = AssessmentApplication,
    ) -> None:
        self.repository = repository
        self._application_factory = application_factory
        self.application = application_factory(repository)
        self.screen = UIScreen.HOME
        self.message = ""
        self.profile_index = 0
        self.subject_index = 0
        self.set_index = 0
        self.detail_page = 0
        self.detail_return_screen = UIScreen.QUESTION
        self.result: ScoreResult | None = None
        self.review_items: tuple[ReviewItem, ...] = ()
        self.review_index = 0
        self.refresh_catalog()

    def refresh_catalog(self) -> None:
        self.profiles = self.repository.list_profiles()
        self.question_sets = self.repository.list_question_sets()
        self.subjects = tuple(sorted({question_set.subject for question_set in self.question_sets}))
        self.profile_index = min(self.profile_index, max(0, len(self.profiles) - 1))
        self.subject_index = min(self.subject_index, max(0, len(self.subjects) - 1))
        self.set_index = min(self.set_index, max(0, len(self.subject_question_sets) - 1))
        if not self.question_sets:
            self.message = (
                "No question sets installed. Import content/sample_biology.json with "
                "python -m tools.import_pack."
            )
        elif not self.profiles:
            self.message = "No profile found. Confirm to create a development profile."
        else:
            self.message = ""

    @property
    def selected_profile(self) -> Profile | None:
        return self.profiles[self.profile_index] if self.profiles else None

    @property
    def selected_question_set(self) -> QuestionSet | None:
        sets = self.subject_question_sets
        return sets[self.set_index] if sets else None

    @property
    def selected_subject(self) -> str | None:
        return self.subjects[self.subject_index] if self.subjects else None

    @property
    def subject_question_sets(self) -> tuple[QuestionSet, ...]:
        subject = self.selected_subject
        return tuple(item for item in self.question_sets if item.subject == subject)

    @property
    def can_resume(self) -> bool:
        profile = self.selected_profile
        return bool(profile and self.repository.find_in_progress_attempt(profile.id))

    @property
    def resume_summary(self) -> tuple[str, int, int] | None:
        profile = self.selected_profile
        if profile is None:
            return None
        attempt = self.repository.find_in_progress_attempt(profile.id)
        if attempt is None:
            return None
        question_set = self.repository.get_question_set(attempt.set_id, attempt.set_version)
        title = question_set.title if question_set else attempt.set_id
        total = len(self.repository.get_attempt_question_order(attempt.id))
        answered = sum(
            response.selected_key is not None
            for response in self.repository.get_attempt_responses(attempt.id)
        )
        return title, answered, total

    def create_development_profile(self) -> Profile:
        profile = Profile(id=str(uuid4()), display_name="Development Student")
        self.repository.create_profile(profile)
        self.refresh_catalog()
        self.profile_index = len(self.profiles) - 1
        return profile

    def handle(self, action: Action) -> None:
        """Apply one canonical action and convert expected failures into UI feedback."""
        self.message = ""
        try:
            if self.screen is UIScreen.HOME:
                self._handle_profile(action)
            elif self.screen is UIScreen.SUBJECT:
                self._handle_subject(action)
            elif self.screen is UIScreen.QUESTION_SET:
                self._handle_question_set(action)
            elif self.screen is UIScreen.QUESTION:
                self._handle_question(action)
            elif self.screen is UIScreen.QUESTION_DETAIL:
                self._handle_detail(action)
            elif self.screen is UIScreen.CONFIDENCE:
                self._handle_confidence(action)
            elif self.screen is UIScreen.SUBMIT_CONFIRM:
                self._handle_submit(action)
            elif self.screen is UIScreen.RESULT:
                self._handle_result(action)
            elif self.screen is UIScreen.REVIEW:
                self._handle_review(action)
            elif self.screen is UIScreen.ERROR and action is Action.BACK:
                self._return_home()
        except NavigationBoundary as error:
            self.message = str(error)
        except (RuntimeError, ValueError) as error:
            self.message = str(error)
            self.screen = UIScreen.ERROR

    def _handle_profile(self, action: Action) -> None:
        if action in {Action.PREV, Action.SELECT_A} and self.profiles:
            self.profile_index = (self.profile_index - 1) % len(self.profiles)
        elif action in {Action.NEXT, Action.SELECT_B} and self.profiles:
            self.profile_index = (self.profile_index + 1) % len(self.profiles)
        elif action is Action.CONFIRM:
            if not self.profiles:
                self.create_development_profile()
                self.message = "Development Student created. Continue to choose a subject."
                return
            self.screen = UIScreen.SUBJECT

    def _handle_subject(self, action: Action) -> None:
        if action in {Action.PREV, Action.SELECT_A} and self.subjects:
            self.subject_index = (self.subject_index - 1) % len(self.subjects)
            self.set_index = 0
        elif action in {Action.NEXT, Action.SELECT_B} and self.subjects:
            self.subject_index = (self.subject_index + 1) % len(self.subjects)
            self.set_index = 0
        elif action is Action.CONFIRM:
            if self.subjects:
                self.screen = UIScreen.QUESTION_SET
            else:
                self.message = "No subjects are available. Install a validated question pack."
        elif action in {Action.BACK, Action.MENU}:
            self.screen = UIScreen.PROFILE

    def _handle_question_set(self, action: Action) -> None:
        sets = self.subject_question_sets
        if action in {Action.PREV, Action.SELECT_A} and sets:
            self.set_index = (self.set_index - 1) % len(sets)
        elif action in {Action.NEXT, Action.SELECT_B} and sets:
            self.set_index = (self.set_index + 1) % len(sets)
        elif action is Action.CONFIRM:
            profile = self.selected_profile
            if profile is None:
                self.message = "Select a local profile first."
                self.screen = UIScreen.PROFILE
            elif self.can_resume:
                resumed = self.application.resume_attempt(profile.id)
                if resumed is None:
                    raise RuntimeError("The in-progress assessment could not be resumed")
                self.screen = UIScreen.QUESTION
            elif self.selected_question_set is None:
                self.message = "No question set is installed for this subject."
            else:
                selected = self.selected_question_set
                self.application.start_test(profile.id, selected.id, selected.version)
                self.screen = UIScreen.QUESTION
        elif action in {Action.BACK, Action.MENU}:
            self.screen = UIScreen.SUBJECT

    def _handle_question(self, action: Action) -> None:
        answer_keys = {
            Action.SELECT_A: "A",
            Action.SELECT_B: "B",
            Action.SELECT_C: "C",
            Action.SELECT_D: "D",
        }
        if action in answer_keys:
            self.application.select_answer(answer_keys[action])  # type: ignore[arg-type]
            self.screen = UIScreen.CONFIDENCE
        elif action is Action.PREV:
            self.application.previous_question()
        elif action is Action.NEXT:
            if self.application.next_question() is None:
                self.screen = UIScreen.SUBMIT_CONFIRM
        elif action is Action.MARK_REVIEW:
            response = self.application.current_response()
            self.application.set_marked_review(not bool(response and response.marked_review))
        elif action is Action.SUBMIT:
            self.application.request_submit()
            self.screen = UIScreen.SUBMIT_CONFIRM
        elif action in {Action.BACK, Action.MENU}:
            self.application.pause()
            self._return_home()
        elif action is Action.CONFIRM:
            self.detail_page = 0
            self.detail_return_screen = UIScreen.QUESTION
            self.screen = UIScreen.QUESTION_DETAIL

    def _handle_detail(self, action: Action) -> None:
        if action is Action.PREV:
            self.detail_page = max(0, self.detail_page - 1)
        elif action is Action.NEXT:
            self.detail_page = min(2, self.detail_page + 1)
        elif action in {Action.BACK, Action.CONFIRM, Action.MENU}:
            self.screen = self.detail_return_screen

    def _handle_confidence(self, action: Action) -> None:
        confidence_actions = {
            Action.SURE: Confidence.SURE,
            Action.NOT_SURE: Confidence.NOT_SURE,
            Action.GUESSING: Confidence.GUESSING,
        }
        if action in confidence_actions:
            self.application.set_confidence(confidence_actions[action])
            self.screen = UIScreen.QUESTION
        elif action in {Action.CONFIRM, Action.BACK}:
            self.application.continue_unrated()
            self.screen = UIScreen.QUESTION

    def _handle_submit(self, action: Action) -> None:
        if action in {Action.SUBMIT, Action.CONFIRM}:
            self.result = self.application.submit()
            self.screen = UIScreen.RESULT
        elif action is Action.BACK:
            self.application.cancel_submit()
            self.screen = UIScreen.QUESTION

    def _handle_result(self, action: Action) -> None:
        if action is Action.CONFIRM:
            self.review_items = self.application.open_review()
            self.review_index = 0
            self.screen = UIScreen.REVIEW
        elif action is Action.BACK:
            self._return_home()

    def _handle_review(self, action: Action) -> None:
        if action is Action.NEXT and self.review_index < len(self.review_items) - 1:
            self.review_index += 1
        elif action is Action.PREV and self.review_index > 0:
            self.review_index -= 1
        elif action is Action.BACK:
            self.application.close_review()
            self.screen = UIScreen.RESULT
        elif action is Action.CONFIRM:
            self.detail_page = 0
            self.detail_return_screen = UIScreen.REVIEW
            self.screen = UIScreen.QUESTION_DETAIL

    @property
    def submit_counts(self) -> tuple[int, int, int]:
        responses = self.application.engine.responses()
        answered = sum(response.selected_key is not None for response in responses)
        total = len(self.application.engine.ordered_question_ids)
        marked = sum(response.marked_review for response in responses)
        return answered, total - answered, marked

    def _return_home(self) -> None:
        self.application = self._application_factory(self.repository)
        self.result = None
        self.review_items = ()
        self.review_index = 0
        self.screen = UIScreen.HOME
        self.refresh_catalog()

    def close(self) -> None:
        """Checkpoint active timing without submitting, leaving the attempt resumable."""
        self.application.pause()
