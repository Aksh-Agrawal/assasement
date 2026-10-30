"""Framework-neutral student UI routing over real application and repository APIs."""

import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from app.assessment import AssessmentApplication
from app.auth.pin import PinUnlock
from app.auth.product_state import account_status
from app.core.engine import NavigationBoundary, ReviewItem
from app.core.models import AttemptStatus, Confidence, Profile, QuestionSet, ScoreResult
from app.data.repo import Repository, SyncStatus
from app.input.actions import Action
from app.ui.router import SETTINGS_ROUTES, UIScreen
from app.version import __version__


@dataclass(frozen=True, slots=True)
class HistoryItem:
    title: str
    subject: str
    score: int | float | None
    maximum: int | float
    completed_at: object
    sync_status: SyncStatus


class LegacyController:
    """Route canonical actions; assessment rules remain in the application service."""

    def __init__(
        self,
        repository: Repository,
        *,
        application_factory: Callable[[Repository], AssessmentApplication] = AssessmentApplication,
        startup: bool = False,
    ) -> None:
        self.repository = repository
        self.student_flow = startup
        self._application_factory = application_factory
        self.application = application_factory(repository)
        self.screen = UIScreen.SPLASH if startup else UIScreen.PROFILE
        self.previous_screen = UIScreen.HOME
        self.message = ""
        self.error_code = "APP-001"
        self.profile_index = 0
        self.subject_index = 0
        self.set_index = 0
        self.dashboard_index = 0
        self.navigator_index = 0
        self.detail_page = 0
        self.detail_return_screen = UIScreen.QUESTION
        self.result: ScoreResult | None = None
        self.review_items: tuple[ReviewItem, ...] = ()
        self.review_index = 0
        self.refresh_catalog()

    def finish_splash(self) -> None:
        if self.screen is UIScreen.SPLASH:
            self.screen = UIScreen.WELCOME

    def refresh_catalog(self) -> None:
        self.profiles = self.repository.list_profiles()
        self.question_sets = self.repository.list_question_sets()
        self.subjects = tuple(sorted({item.subject for item in self.question_sets}))
        self.profile_index = min(self.profile_index, max(0, len(self.profiles) - 1))
        self.subject_index = min(self.subject_index, max(0, len(self.subjects) - 1))
        self.set_index = min(self.set_index, max(0, len(self.subject_question_sets) - 1))
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
        return tuple(item for item in self.question_sets if item.subject == self.selected_subject)

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
        title = question_set.title if question_set else "Assessment"
        total = len(self.repository.get_attempt_question_order(attempt.id))
        answered = sum(
            response.selected_key is not None
            for response in self.repository.get_attempt_responses(attempt.id)
        )
        return title, answered, total

    @property
    def network_label(self) -> str:
        value = (self.repository.get_setting("network_state") or "offline").casefold()
        return {
            "online": "Online",
            "syncing": "Syncing",
            "authentication_required": "Sign-in needed",
        }.get(value, "Offline")

    @property
    def pending_sync_count(self) -> int:
        return self.repository.count_attempts_by_sync_status(
            SyncStatus.PENDING
        ) + self.repository.count_attempts_by_sync_status(SyncStatus.FAILED)

    @property
    def sync_label(self) -> str:
        if self.repository.sync_diagnostic_summary()["attention_required"]:
            return "Sync attention required"
        if self.network_label == "Offline":
            return "Offline"
        return f"{self.pending_sync_count} pending" if self.pending_sync_count else "Synced"

    @property
    def history_items(self) -> tuple[HistoryItem, ...]:
        profile = self.selected_profile
        if profile is None:
            return ()
        items = []
        for attempt in self.repository.list_attempts(
            profile_id=profile.id, status=AttemptStatus.COMPLETED, limit=20
        ):
            question_set = self.repository.get_question_set(attempt.set_id, attempt.set_version)
            if question_set is None:
                title, subject, maximum = "Assessment", "", 0
            else:
                title, subject = question_set.title, question_set.subject
                maximum = len(question_set.questions) * question_set.marking.correct
            items.append(
                HistoryItem(
                    title,
                    subject,
                    attempt.score,
                    maximum,
                    attempt.completed_at,
                    self.repository.get_attempt_sync_state(attempt.id).status,
                )
            )
        return tuple(items)

    @property
    def software_version(self) -> str:
        return __version__

    def create_development_profile(self) -> Profile:
        profile = Profile(id=str(uuid4()), display_name="Student")
        self.repository.create_profile(profile)
        self.refresh_catalog()
        self.profile_index = len(self.profiles) - 1
        return profile

    def handle(self, action: Action) -> None:
        self.message = ""
        try:
            handler = getattr(self, f"_handle_{self.screen.value.casefold()}", None)
            if handler is not None:
                handler(action)
        except NavigationBoundary as error:
            self.message = str(error)
        except (RuntimeError, ValueError) as error:
            self.message = "Your assessment is safe. Please try again."
            self.error_code = "DB-001" if "database" in str(error).casefold() else "APP-001"
            self.previous_screen = self.screen
            self.screen = UIScreen.ERROR

    def _handle_splash(self, _action: Action) -> None:
        self.finish_splash()

    def _handle_welcome(self, action: Action) -> None:
        if action in {Action.CONFIRM, Action.NEXT}:
            self.screen = UIScreen.PROFILE

    def _handle_profile(self, action: Action) -> None:
        if action in {Action.PREV, Action.SELECT_A} and self.profiles:
            self.profile_index = (self.profile_index - 1) % len(self.profiles)
        elif action in {Action.NEXT, Action.SELECT_B} and self.profiles:
            self.profile_index = (self.profile_index + 1) % len(self.profiles)
        elif action is Action.CONFIRM:
            if not self.profiles:
                self.create_development_profile()
                if not self.student_flow:
                    return
            self.dashboard_index = 1 if self.can_resume else 0
            self.screen = UIScreen.HOME if self.student_flow else UIScreen.SUBJECT
        elif action is Action.BACK:
            self.screen = UIScreen.WELCOME

    def _handle_home(self, action: Action) -> None:
        if action is Action.SELECT_A:
            self.dashboard_index = 0
        elif action is Action.SELECT_B and self.can_resume:
            self.dashboard_index = 1
        elif action is Action.SELECT_C:
            self.dashboard_index = 2
        elif action is Action.SELECT_D:
            self.dashboard_index = 3
        elif action in {Action.PREV, Action.NEXT}:
            step = -1 if action is Action.PREV else 1
            self.dashboard_index = (self.dashboard_index + step) % 4
        elif action is Action.CONFIRM:
            if self.dashboard_index == 0:
                self.screen = UIScreen.SUBJECT
            elif self.dashboard_index == 1 and self.can_resume:
                profile = self.selected_profile
                if profile and self.application.resume_attempt(profile.id):
                    self.screen = UIScreen.QUESTION
            elif self.dashboard_index == 2:
                self.screen = UIScreen.HISTORY
            elif self.dashboard_index == 3:
                self.screen = UIScreen.STATUS
        elif action is Action.MENU:
            self.screen = UIScreen.SETTINGS
        elif action is Action.BACK:
            self.screen = UIScreen.PROFILE

    def _handle_subject(self, action: Action) -> None:
        if action in {Action.PREV, Action.SELECT_A} and self.subjects:
            self.subject_index = (self.subject_index - 1) % len(self.subjects)
            self.set_index = 0
        elif action in {Action.NEXT, Action.SELECT_B} and self.subjects:
            self.subject_index = (self.subject_index + 1) % len(self.subjects)
            self.set_index = 0
        elif action is Action.CONFIRM and self.subjects:
            self.screen = UIScreen.QUESTION_SET
        elif action in {Action.BACK, Action.MENU}:
            self.screen = UIScreen.HOME

    def _handle_question_set(self, action: Action) -> None:
        sets = self.subject_question_sets
        if action in {Action.PREV, Action.SELECT_A} and sets:
            self.set_index = (self.set_index - 1) % len(sets)
        elif action in {Action.NEXT, Action.SELECT_B} and sets:
            self.set_index = (self.set_index + 1) % len(sets)
        elif action is Action.CONFIRM and self.selected_question_set:
            if self.student_flow:
                self.screen = UIScreen.INSTRUCTIONS
            else:
                profile, selected = self.selected_profile, self.selected_question_set
                if profile is None:
                    return
                if self.can_resume:
                    self.application.resume_attempt(profile.id)
                else:
                    self.application.start_test(profile.id, selected.id, selected.version)
                self.screen = UIScreen.QUESTION
        elif action in {Action.BACK, Action.MENU}:
            self.screen = UIScreen.SUBJECT

    def _handle_instructions(self, action: Action) -> None:
        if action is Action.CONFIRM:
            profile, selected = self.selected_profile, self.selected_question_set
            if profile is None or selected is None:
                raise RuntimeError("Assessment content is unavailable")
            if self.can_resume:
                self.application.resume_attempt(profile.id)
            else:
                self.application.start_test(profile.id, selected.id, selected.version)
            self.screen = UIScreen.QUESTION
        elif action is Action.BACK:
            self.screen = UIScreen.QUESTION_SET

    def _handle_question(self, action: Action) -> None:
        answers = {
            Action.SELECT_A: "A",
            Action.SELECT_B: "B",
            Action.SELECT_C: "C",
            Action.SELECT_D: "D",
        }
        if action in answers:
            self.application.select_answer(answers[action])  # type: ignore[arg-type]
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
        elif action is Action.MENU:
            if self.student_flow:
                self.navigator_index = self.application.engine.current_index
                self.screen = UIScreen.QUESTION_NAVIGATOR
            else:
                self.application.pause()
                self._return_home()
        elif action is Action.BACK:
            self.application.pause()
            self.screen = UIScreen.HOME
        elif action is Action.CONFIRM:
            self.detail_page = 0
            self.detail_return_screen = UIScreen.QUESTION
            self.screen = UIScreen.QUESTION_DETAIL

    def _handle_question_navigator(self, action: Action) -> None:
        total = len(self.application.engine.ordered_question_ids)
        if action is Action.PREV:
            self.navigator_index = max(0, self.navigator_index - 1)
        elif action is Action.NEXT:
            self.navigator_index = min(total - 1, self.navigator_index + 1)
        elif action is Action.CONFIRM:
            self.application.go_to_question(self.navigator_index)
            self.screen = UIScreen.QUESTION
        elif action is Action.BACK:
            self.screen = UIScreen.QUESTION

    def _handle_question_detail(self, action: Action) -> None:
        if action is Action.PREV:
            self.detail_page = max(0, self.detail_page - 1)
        elif action is Action.NEXT:
            self.detail_page = min(2, self.detail_page + 1)
        elif action in {Action.BACK, Action.CONFIRM, Action.MENU}:
            self.screen = self.detail_return_screen

    def _handle_confidence(self, action: Action) -> None:
        choices = {
            Action.SURE: Confidence.SURE,
            Action.NOT_SURE: Confidence.NOT_SURE,
            Action.GUESSING: Confidence.GUESSING,
        }
        if action in choices:
            self.application.set_confidence(choices[action])
            self.screen = UIScreen.QUESTION
        elif action in {Action.CONFIRM, Action.BACK}:
            self.application.continue_unrated()
            self.screen = UIScreen.QUESTION

    def _handle_submit_confirm(self, action: Action) -> None:
        if action in {Action.SUBMIT, Action.CONFIRM}:
            self.result = self.application.submit()
            self.screen = UIScreen.RESULT
        elif action is Action.BACK:
            self.application.cancel_submit()
            self.screen = UIScreen.QUESTION
        elif action is Action.MENU:
            self.application.cancel_submit()
            self.navigator_index = self.application.engine.current_index
            self.screen = UIScreen.QUESTION_NAVIGATOR

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

    def _handle_history(self, action: Action) -> None:
        if action in {Action.BACK, Action.MENU}:
            self.screen = UIScreen.HOME

    def _handle_status(self, action: Action) -> None:
        if action in {Action.BACK, Action.MENU}:
            self.screen = UIScreen.HOME

    def _handle_settings(self, action: Action) -> None:
        if action in {Action.BACK, Action.MENU}:
            self.screen = UIScreen.HOME
        elif action is Action.CONFIRM:
            current = self.repository.get_setting("text_size") or "standard"
            self.repository.set_setting(
                "text_size", "large" if current == "standard" else "standard"
            )
            self.message = "Text size preference saved."

    def _handle_error(self, action: Action) -> None:
        if action is Action.BACK:
            self._return_home()
        elif action is Action.CONFIRM:
            self.screen = self.previous_screen

    @property
    def submit_counts(self) -> tuple[int, int, int]:
        responses = self.application.engine.responses()
        answered = sum(item.selected_key is not None for item in responses)
        total = len(self.application.engine.ordered_question_ids)
        marked = sum(item.marked_review for item in responses)
        return answered, total - answered, marked

    def _return_home(self) -> None:
        self.application = self._application_factory(self.repository)
        self.result = None
        self.review_items = ()
        self.review_index = 0
        self.screen = UIScreen.HOME if self.student_flow else UIScreen.PROFILE
        self.refresh_catalog()

    def close(self) -> None:
        self.application.pause()


@dataclass(frozen=True, slots=True)
class Choice:
    label: str
    command: str
    value: object = None
    enabled: bool = True


class UIController(LegacyController):
    """Document-defined appliance flow using the existing assessment application.

    ``startup=False`` retains the original framework-neutral integration API.
    The GUI entry point always requests the complete device flow.
    """

    def __init__(
        self, repository, *, application_factory=AssessmentApplication, startup=False, device=None
    ):
        self.institute_assignment = None
        self.chapter_index = 0
        self.focus = 0
        self.scroll = 0
        self.page_count = 1
        self.text_value = ""
        self.keyboard_index = 0
        self.keyboard_mode = 0
        self.show_password = False
        self.selected_wifi = None
        self.all_review_items = ()
        self.review_filter = "all"
        self.pair_return = UIScreen.PROFILE
        self.diagnostic_return = UIScreen.SETTINGS
        self.next_pair_poll = 0.0
        self.authorized_profile = None
        self.device = device
        self.startup_rows = ()
        super().__init__(repository, application_factory=application_factory, startup=startup)
        self.pin_service = PinUnlock(repository)

    def route(self, screen):
        self.screen = screen
        self.focus = self.scroll = self.detail_page = 0
        self.page_count = 1
        self.message = ""

    def refresh_catalog(self):
        super().refresh_catalog()
        if self.student_flow and os.environ.get("ASSESS_MAINTENANCE") != "1":
            context = self.repository.get_student_account_context()
            cached = json.loads(self.repository.get_setting("account_profiles") or "{}")
            active_ids = {p["local_profile_id"] for p in cached.get("profiles", [])}
            self.profiles = tuple(p for p in self.profiles if context and
                p.cloud_account_id == context["cloud_account_id"] and p.id in active_ids)
            self.profile_index = min(self.profile_index, max(0, len(self.profiles) - 1))
        if os.environ.get("ASSESS_MAINTENANCE") == "1" and getattr(self, "legacy_mode", False):
            self.profiles = tuple(p for p in self.profiles if p.ownership_state == "legacy_unclaimed")
            self.profile_index = min(self.profile_index, max(0, len(self.profiles) - 1))
        if self.student_flow:
            profile_id = self.selected_profile.id if self.selected_profile else None
            self.question_sets = self.repository.visible_question_sets(profile_id)
            self.subjects = tuple(sorted({p.subject for p in self.question_sets} |
                                         {p.subject for p in self.remote_packs}))
            self.subject_index = min(self.subject_index, max(0, len(self.subjects) - 1))

    @property
    def remote_packs(self):
        profile = self.selected_profile
        if profile and profile.ownership_state == "owned":
            from app.content.catalog import RemotePack
            return tuple(RemotePack.from_dict(p) for p in
                         self.repository.profile_library_catalog(profile.id))
        if self.device and getattr(self.device, "catalog_profile_id", None) is None:
            return self.device.catalog
        return ()

    @property
    def resume_summary(self):
        summary = super().resume_summary
        if not self.student_flow or not summary or not self.selected_profile:
            return summary
        attempt = self.repository.find_in_progress_attempt(self.selected_profile.id)
        question_set = self.repository.get_question_set(attempt.set_id, attempt.set_version)
        title = f"{question_set.subject} / {question_set.chapter}" if question_set else summary[0]
        return title, summary[1], summary[2]

    def finish_splash(self):
        if self.screen is UIScreen.STARTUP:
            # The process entry point runs StartupSession before constructing us.
            # Direct controller use still performs a real local safety check.
            if not self.repository.quick_check().ok:
                self.route(UIScreen.RECOVERY)
            else:
                if self.repository.get_student_account_context() or os.environ.get("ASSESS_MAINTENANCE") == "1":
                    self.route(UIScreen.PROFILE)
                    self._job("account_sync")
                else:
                    self.route(UIScreen.PAIRING)
                    if self.device and self.device.credentials.load_safe():
                        self._job("account_sync")
                    else:
                        self._job("pair_request", device_id=self.repository.get_or_create_device_id())

    @property
    def chapters(self):
        return tuple(
            sorted(
                {
                    s.chapter
                    for s in (*self.question_sets, *self.remote_packs)
                    if s.subject == self.selected_subject
                }
            )
        )

    @property
    def selected_chapter(self):
        return (
            self.chapters[min(self.chapter_index, len(self.chapters) - 1)]
            if self.chapters
            else None
        )

    @property
    def subject_question_sets(self):
        sets = super().subject_question_sets
        if not getattr(self, "student_flow", False):
            return sets
        return tuple(s for s in sets if s.chapter == self.selected_chapter)

    @property
    def network_label(self):
        verified = account_status(self.repository,
            verified_this_run=bool(self.device and self.device.account_verified)) == "Connected"
        measured = bool(self.device and self.device.network and self.device.network.backend_reachable
                        and time.monotonic() - self.device.network_checked_at < 180)
        if verified or measured:
            return "Cloud: Available"
        # A persisted flag is not proof of a current connection.
        return "Cloud: Unreachable (Wi-Fi connected)" if self.device and self.device.wifi_connected else "Cloud: Offline / unverified"

    @property
    def greeting(self):
        hour = datetime.now().hour
        return "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"

    @property
    def choices(self):
        providers = {
            UIScreen.PROFILE: self._profile_choices,
            UIScreen.HOME: self._home_choices,
            UIScreen.SUBJECTS: self._subject_choices,
            UIScreen.INSTITUTE_WORK: self._institute_choices,
            UIScreen.CHAPTERS: self._chapter_choices,
            UIScreen.PACKS: self._pack_choices,
            UIScreen.TEST_SETUP: self._setup_choices,
            UIScreen.SETTINGS: self._settings_choices,
            UIScreen.ASSESSMENT_MENU: self._assessment_choices,
            UIScreen.LEAVE_CONFIRM: lambda: (
                Choice("Continue test", "return_question"),
                Choice("Save and go Home", "leave"),
            ),
            UIScreen.RESULT: self._result_choices,
            UIScreen.WIFI: self._wifi_choices,
            UIScreen.SYNC: lambda: (
                Choice("Sync Now", "job", "sync"),
                Choice("Check connection", "job", "network"),
            ),
            UIScreen.LINK_CONFIRM: lambda: (
                Choice("Confirm link", "profile_claim"),
                Choice("Back", "route", UIScreen.LINK_PROFILE),
            ),
            UIScreen.ACCOUNT: self._account_choices,
            UIScreen.CONTENT_UPDATES: self._content_choices,
            UIScreen.SOFTWARE_UPDATE: self._update_choices,
            UIScreen.DIAGNOSTICS: lambda: (
                Choice("Run Check", "job", "diagnostics"),
                Choice("Export Support Bundle", "job", "export"),
            ),
            UIScreen.DEVICE_INFO: lambda: (Choice("Diagnostics", "route", UIScreen.DIAGNOSTICS),),
            UIScreen.ABOUT: lambda: (Choice("Licences", "licences"),),
            UIScreen.PAIRING: lambda: (Choice("Refresh Code", "request_pair"), Choice("Wi-Fi", "route", UIScreen.WIFI)),
            UIScreen.RECOVERY: lambda: (
                Choice("Retry checks", "retry"),
                Choice("Diagnostics", "route", UIScreen.DIAGNOSTICS),
                Choice("Recovery options", "recovery_options"),
            ),
        }
        return tuple(providers.get(self.screen, lambda: ())())

    def _profile_choices(self):
        result = tuple(Choice(p.display_name, "profile", i) for i, p in enumerate(self.profiles))
        if self.repository.get_student_account_context():
            cached = json.loads(self.repository.get_setting("account_profiles") or "{}")
            if cached.get("profile_count", 3) < 3:
                result += (Choice("+ Create Profile", "route", UIScreen.ADD_PROFILE),)
            result += (Choice("Sync Profiles", "job", "account_sync"),)
        else:
            result += (Choice("Connect Raspberry Pi", "pair"),)
        if os.environ.get("ASSESS_MAINTENANCE") == "1":
            result += (Choice("Link legacy Study Profile", "profile_link"),)
            result += (Choice("Legacy Profiles / Import", "legacy_profiles"),)
        return result

    def _account_choices(self):
        if not self.repository.get_student_account_context():
            return ((Choice("Link legacy Study Profile", "profile_link"),) if os.environ.get("ASSESS_MAINTENANCE") == "1" else ()) + (Choice("Connect Raspberry Pi", "pair"),)
        return tuple(c for c in self._profile_choices() if c.command != "profile") + (
            Choice("Choose Study Profile", "route", UIScreen.PROFILE),
            Choice("Disconnect Device" if not getattr(self, "disconnect_pending", False)
                   else "Confirm Disconnect Device", "account_disconnect"),)

    def _home_choices(self):
        resume = self.resume_summary
        label = f"CONTINUE TEST\n{resume[0]}" if resume else "CONTINUE TEST\nNo unfinished test"
        return (
            Choice(label, "resume", enabled=bool(resume)),
            Choice("Practice & Downloads\nChoose subject and chapter", "route", UIScreen.SUBJECTS),
            Choice("Institute Work", "route", UIScreen.INSTITUTE_WORK),
            Choice("History", "route", UIScreen.PROGRESS),
            Choice("Settings", "route", UIScreen.SETTINGS),
        )

    @property
    def selected_question_set(self):
        a = getattr(self, "institute_assignment", None)
        if a and self.selected_profile and a["local_profile_id"] == self.selected_profile.id:
            return self.repository.get_question_set(a["set_id"], a["version"])
        return super().selected_question_set

    def _institute_choices(self):
        p = self.selected_profile
        if not p:
            return ()
        choices = [Choice("Refresh Institute Work", "institute_refresh")]
        for a in self.repository.institute_work(p.id):
            installed = self.repository.get_question_set(a["set_id"], a["version"])
            choices.append(Choice(f"{a['title']} | {a['institute_name']}\n" +
                ("Downloaded / Start" if installed else "Download for offline practice"),
                "institute_start" if installed else "institute_download", a))
        return tuple(choices)

    def _subject_choices(self):
        result = []
        for index, subject in enumerate(self.subjects):
            sets = tuple(s for s in self.question_sets if s.subject == subject)
            result.append(
                Choice(
                    f"{subject}\n{len({s.chapter for s in sets})} chapters | {sum(len(s.questions) for s in sets)} questions",
                    "subject",
                    index,
                )
            )
        return result

    def _chapter_choices(self):
        return tuple(
            Choice(
                f"{chapter}\n{sum(s.chapter == chapter and s.subject == self.selected_subject for s in self.question_sets)} local sets",
                "chapter",
                i,
            )
            for i, chapter in enumerate(self.chapters)
        )

    def _pack_choices(self):
        local = self.subject_question_sets
        choices = []
        for i, s in enumerate(local):
            newer = any(p.set_id == s.id and p.version > s.version for p in self.remote_packs)
            state = "Downloaded | Update available" if newer else "Downloaded"
            choices.append(
                Choice(
                    f"{s.title}\n{state} | {len(s.questions)} questions | v{s.version}", "pack", i
                )
            )
        for pack in self.remote_packs:
            if pack.subject != self.selected_subject or pack.chapter != self.selected_chapter:
                continue
            if any(s.id == pack.set_id and s.version == pack.version for s in local):
                continue
            state = (
                "Update available" if any(s.id == pack.set_id for s in local) else "Not downloaded"
            )
            failed = self.device.download_state.get((pack.set_id, pack.version))
            if failed in {"VALIDATION_FAILED", "HASH_MISMATCH"}:
                state = "Validation failed"
            if self.device.network and self.device.network.backend_reachable is False:
                state += " | Unavailable offline"
            if (
                self.device.busy
                and self.device.operation == "download"
                and getattr(self, "downloading_pack", None) == (pack.set_id, pack.version)
            ):
                state = "Downloading"
            choices.append(
                Choice(
                    f"Get {pack.title}\n{state} | {pack.question_count} questions | v{pack.version}",
                    "download",
                    pack,
                )
            )
        return tuple(choices)

    def _setup_choices(self):
        return (Choice("Resume existing test" if self.can_resume else "Start Test", "start"),) + (
            (Choice("Start New", "new_test"),) if self.can_resume else ()
        )

    def _settings_choices(self):
        return tuple(
            Choice(label, "route", route)
            for label, route in zip(
                (
                    "Account & Profiles | " + account_status(self.repository,
                        verified_this_run=bool(self.device and self.device.account_verified)),
                    "Wi-Fi",
                    f"Sync | {self.pending_sync_count} pending",
                    "Content & Downloads",
                    f"Software Update | {self.software_version}",
                    "Device",
                    "Diagnostics",
                    "About",
                ),
                SETTINGS_ROUTES,
                strict=True,
            )
        )

    def _assessment_choices(self):
        return (
            Choice("Question Navigator", "navigator"),
            Choice("Resume Assessment", "return_question"),
            Choice("Submit Test", "submit"),
            Choice("Device Status", "assessment_status"),
            Choice("Home", "route", UIScreen.LEAVE_CONFIRM),
        )

    def _result_choices(self):
        result = self.result
        return (
            Choice("Review All", "review", "all"),
            Choice("Review Wrong", "review", "wrong"),
            Choice(
                f"Sure but wrong: {len(result.sure_but_wrong_question_ids) if result else 0}",
                "review",
                "sure_wrong",
            ),
            Choice(
                f"Guessed right: {len(result.guessed_right_question_ids) if result else 0}",
                "review",
                "guessed_right",
            ),
            Choice("Review Guessed", "review", "guessed"),
            Choice("Done", "done"),
        )

    def _wifi_choices(self):
        device = self.device
        result = [
            Choice("Scan again", "job", "wifi_scan", bool(device and device.wifi.available)),
            Choice("Check internet", "job", "network"),
        ]
        if device:
            result += [
                Choice(f"{name}\nSaved network", "wifi_saved", name)
                for name in device.saved_networks
            ]
            result += [
                Choice(f"{n.ssid}\nSignal {n.signal}% | {n.security}", "wifi_select", n.ssid)
                for n in device.networks
            ]
        return result

    def _content_choices(self):
        result = [Choice("Check available content", "job", "catalog")]
        result += [Choice(f"{pack.subject} / {pack.title} | v{pack.version} | Installed",
                          "local_pack", enabled=False) for pack in self.question_sets]
        if self.device:
            local = {(s.id, s.version) for s in self.question_sets}
            for pack in self.remote_packs:
                newest = max(
                    (s.version for s in self.question_sets if s.id == pack.set_id), default=0
                )
                status = (
                    "Downloaded"
                    if (pack.set_id, pack.version) in local
                    else "Update available"
                    if newest
                    else "Not downloaded"
                )
                state = self.device.download_state.get((pack.set_id, pack.version))
                if state and state != "INSTALLED":
                    status = (
                        "Validation failed"
                        if state in {"VALIDATION_FAILED", "HASH_MISMATCH"}
                        else "Failed - retry available"
                    )
                if (
                    self.device.busy
                    and self.device.operation == "download"
                    and getattr(self, "downloading_pack", None) == (pack.set_id, pack.version)
                ):
                    status = "Downloading"
                result.append(
                    Choice(
                        f"{pack.subject} / {pack.title}\nv{newest} > v{pack.version} | {pack.size_bytes / 2**20:.1f} MB | {status}",
                        "download",
                        pack,
                        (pack.set_id, pack.version) not in local,
                    )
                )
        return result

    def _update_choices(self):
        device = self.device
        return (
            Choice("Check Now", "job", "update_check"),
            Choice(
                "Download and Verify",
                "update_download",
                enabled=bool(device and device.available_update),
            ),
            Choice("Install & Restart", "update_install", enabled=False),
        )

    def handle(self, action, payload=None):
        if not self.student_flow:
            return super().handle(action)
        self.message = ""
        try:
            if payload is not None:
                kind, value = payload
                if kind == "choice":
                    choices = self.choices
                    if (
                        isinstance(value, int)
                        and 0 <= value < len(choices)
                        and choices[value].enabled
                    ):
                        self.focus = value
                        self._activate(choices[value])
                    return
                if kind == "text":
                    self.handle_text(str(value))
                    return
                if kind == "question" and self.screen is UIScreen.QUESTION_NAV:
                    self.application.go_to_question(value)
                    self.route(UIScreen.QUESTION)
                    return
                if kind == "scroll":
                    self.scroll = max(0, self.scroll + int(value))
                    return
                if kind == "command":
                    self._command(str(value))
                    return
            handlers = {
                UIScreen.QUESTION: self._device_question,
                UIScreen.CONFIDENCE: self._device_confidence,
                UIScreen.SUBMIT_CONFIRM: self._device_submit,
                UIScreen.QUESTION_NAV: self._device_navigator,
                UIScreen.REVIEW: self._device_review,
                UIScreen.QUESTION_DETAIL: self._device_detail,
                UIScreen.LINK_PROFILE: self._device_text,
                UIScreen.PIN: self._device_text,
                UIScreen.ADD_PROFILE: self._device_text,
                UIScreen.PROGRESS: self._device_progress,
            }
            if self.screen is UIScreen.WIFI and self.selected_wifi:
                self._device_text(action)
            elif self.screen in handlers:
                handlers[self.screen](action)
            elif action in {Action.BACK, Action.MENU}:
                if action is Action.MENU and self.screen is UIScreen.HOME:
                    self.route(UIScreen.SETTINGS)
                else:
                    self._back()
            elif action in {Action.PREV, Action.NEXT}:
                choices = self.choices
                if choices:
                    self.focus = (self.focus + (-1 if action is Action.PREV else 1)) % len(choices)
            elif action in {Action.CONFIRM, Action.SELECT_A}:
                choices = self.choices
                if choices and choices[self.focus % len(choices)].enabled:
                    self._activate(choices[self.focus % len(choices)])
        except NavigationBoundary as error:
            self.message = str(error)
        except (RuntimeError, ValueError, OSError):
            self.message = "Action could not complete. Your saved assessment is preserved."

    def _activate(self, choice):
        command, value = choice.command, choice.value
        if command == "route":
            if value in {UIScreen.SUBJECTS, UIScreen.INSTITUTE_WORK, UIScreen.HOME}:
                self.institute_assignment = None
            self.route(value)
            if value is UIScreen.HOME:
                self.focus = 0 if self.can_resume else 1
        elif command == "profile":
            self.institute_assignment = None
            self.profile_index = value
            self.chapter_index = self.set_index = self.subject_index = 0
            self.refresh_catalog()
            self.text_value = ""
            if self.pin_service.protected(self.selected_profile.id):
                self.route(UIScreen.PIN)
            else:
                self._unlocked()
        elif command == "institute_refresh":
            self._job("institute_refresh", local_profile_id=self.selected_profile.id)
        elif command == "institute_download":
            self._job("institute_download", local_profile_id=self.selected_profile.id,
                assignment_id=value["assignment_id"])
        elif command == "institute_start":
            self.institute_assignment = {**value, "local_profile_id": self.selected_profile.id}
            self.route(UIScreen.TEST_SETUP)
        elif command == "subject":
            self.subject_index, self.chapter_index, self.set_index = value, 0, 0
            self.route(UIScreen.CHAPTERS)
        elif command == "chapter":
            self.chapter_index, self.set_index = value, 0
            self.route(UIScreen.PACKS)
        elif command == "pack":
            self.set_index = value
            self.route(UIScreen.TEST_SETUP)
        elif command in {"start", "resume"}:
            self._start_or_resume()
        elif command == "new_test":
            self.message = (
                "Finish your existing test before starting another. It has been preserved."
            )
        elif command == "navigator":
            self.navigator_index = self.application.engine.current_index
            self.route(UIScreen.QUESTION_NAV)
        elif command == "return_question":
            self.application.go_to_question(self.application.engine.current_index)
            self.route(UIScreen.QUESTION)
        elif command == "submit":
            self.application.request_submit()
            self.route(UIScreen.SUBMIT_CONFIRM)
        elif command == "leave":
            self.application.pause()
            self._return_home()
            self.route(UIScreen.HOME)
            self.focus = 0
        elif command == "assessment_status":
            self.diagnostic_return = UIScreen.ASSESSMENT_MENU
            self.route(UIScreen.DEVICE_INFO)
        elif command == "review":
            self._open_filtered_review(value)
        elif command == "done":
            self._return_home()
            self.route(UIScreen.HOME)
            self.focus = 1
        elif command == "job":
            self._job(value)
        elif command == "legacy_profiles" and os.environ.get("ASSESS_MAINTENANCE") == "1":
            self.legacy_mode = True
            self.profiles = tuple(p for p in self.repository.list_profiles() if p.ownership_state == "legacy_unclaimed")
            self.route(UIScreen.PROFILE)
        elif command == "account_disconnect":
            if getattr(self, "disconnect_pending", False):
                self._job("account_disconnect")
                self.disconnect_pending = False
            else:
                self.disconnect_pending = True
                self.message = "Confirm disconnect. Profiles and history will be preserved."
        elif command == "profile_link":
            if self.selected_profile is None:
                self.message = "Select a local profile first."
                return
            if self.selected_profile.link_state == "linked":
                self.message = "This profile is already linked. Unlink explicitly before relinking."
            else:
                self.text_value = ""
                self.route(UIScreen.LINK_PROFILE)
        elif command == "profile_claim":
            code, self.text_value = self.text_value, ""
            self._job("profile_claim", code=code, local_profile_id=self.selected_profile.id)
            self.route(UIScreen.ACCOUNT)
        elif command == "profile_status":
            self._job("profile_status", local_profile_id=self.selected_profile.id)
        elif command == "profile_unlink":
            if getattr(self, "unlink_pending", False):
                self._job("profile_unlink", local_profile_id=self.selected_profile.id)
                self.unlink_pending = False
            else:
                self.unlink_pending = True
                self.message = "Confirm unlink. Saved assessments and the device credential remain."
        elif command == "pair":
            self.pair_return = self.screen
            self.route(UIScreen.PAIRING)
        elif command == "request_pair":
            self._job("pair_request", device_id=self.repository.get_or_create_device_id())
        elif command == "remove_pair_confirm":
            self.remove_pair_pending = not getattr(self, "remove_pair_pending", False)
            self.message = (
                "Select Confirm remove pairing. Local profiles and attempts remain."
                if self.remove_pair_pending
                else "Removal cancelled."
            )
        elif command == "remove_pair" and getattr(self, "remove_pair_pending", False):
            if self.device:
                self.device.credentials.clear()
            self.remove_pair_pending = False
            self.focus = 0
            self.message = "Pairing removed. Your local profiles and assessments are preserved."
        elif command in {"wifi_select", "wifi_saved"}:
            self.selected_wifi = (value, command == "wifi_saved")
            self.text_value = ""
        elif command == "download":
            self.downloading_pack = (value.set_id, value.version)
            self._job("download", pack=value)
        elif command == "update_download":
            self._job("update_download", update=self.device.available_update)
        elif command == "update_install":
            self.message = "Update verified and staged. Automatic restart requires the device release launcher."
        elif command == "licences":
            self.message = (
                "Application licence not yet selected. See LICENSE; pygame-ce uses LGPL 2.1."
            )
        elif command == "recovery_options":
            self.message = "Keep existing data. Ask support to restore a verified backup using the recovery guide."

    def _job(self, operation, **args):
        if operation in {"catalog", "download"} and self.selected_profile:
            args["local_profile_id"] = self.selected_profile.id
        if self.device:
            self.device.start(operation, **args)
            self.message = self.device.message
        else:
            self.message = (
                "Device service unavailable in this session. Local assessment is available."
            )

    def _unlocked(self):
        self.refresh_catalog()
        self.authorized_profile = self.selected_profile.id
        self.route(UIScreen.HOME)
        self.focus = 0 if self.can_resume else 1

    def _start_or_resume(self):
        profile = self.selected_profile
        if not profile or self.authorized_profile != profile.id:
            self.route(UIScreen.PROFILE)
            return
        self.application = self._application_factory(self.repository)
        if self.can_resume:
            self.application.resume_attempt(profile.id)
        elif self.selected_question_set:
            selected = self.selected_question_set
            self.application.start_test(profile.id, selected.id, selected.version,
                institute_assignment_id=self.institute_assignment["assignment_id"] if self.institute_assignment else None)
        else:
            self.message = "No downloaded set is available."
            return
        self.route(UIScreen.QUESTION)

    def _device_question(self, action):
        if action in {Action.BACK, Action.MENU}:
            self.application.pause()
            self.route(
                UIScreen.LEAVE_CONFIRM if action is Action.BACK else UIScreen.ASSESSMENT_MENU
            )
        else:
            self._handle_question(action)
            self.scroll = 0

    def _device_confidence(self, action):
        if action is Action.MENU:
            action = Action.BACK
        action = {
            Action.SELECT_A: Action.SURE,
            Action.SELECT_B: Action.NOT_SURE,
            Action.SELECT_C: Action.GUESSING,
        }.get(action, action)
        self._handle_confidence(action)

    def _device_submit(self, action):
        # Explicit final action only. Enter/A continues; T or the labelled touch control submits.
        if action in {Action.CONFIRM, Action.SELECT_A}:
            action = Action.BACK
        self._handle_submit_confirm(action)
        if self.screen is UIScreen.RESULT:
            self.focus = 0
        self.scroll = 0

    def _device_navigator(self, action):
        if action is Action.SELECT_A:
            action = Action.CONFIRM
        if action is Action.MENU:
            self.route(UIScreen.ASSESSMENT_MENU)
        else:
            self._handle_question_navigator(action)

    def _open_filtered_review(self, filter_name):
        if not self.all_review_items:
            self.all_review_items = self.application.open_review()
        self.review_filter = filter_name
        predicates = {
            "all": lambda item: True,
            "wrong": lambda item: item.outcome == "wrong",
            "sure_wrong": lambda item: item.question.id in self.result.sure_but_wrong_question_ids,
            "guessed_right": lambda item: (
                item.question.id in self.result.guessed_right_question_ids
            ),
            "guessed": lambda item: (
                item.response and item.response.confidence is Confidence.GUESSING
            ),
        }
        self.review_items = tuple(
            item for item in self.all_review_items if predicates[filter_name](item)
        )
        self.review_index = 0
        self.route(UIScreen.REVIEW)

    def _device_review(self, action):
        if action in {Action.BACK, Action.MENU}:
            self.application.close_review()
            self.all_review_items = ()
            self.route(UIScreen.RESULT)
        elif action is Action.SELECT_A:
            self.detail_return_screen = UIScreen.REVIEW
            self.route(UIScreen.QUESTION_DETAIL)
        else:
            self._handle_review(action)
            self.scroll = 0

    def _return_home(self):
        super()._return_home()
        self.all_review_items = ()

    def _device_detail(self, action):
        if action is Action.PREV:
            self.detail_page = max(0, self.detail_page - 1)
        elif action is Action.NEXT:
            self.detail_page = min(self.page_count - 1, self.detail_page + 1)
        elif action in {Action.BACK, Action.MENU, Action.CONFIRM, Action.SELECT_A}:
            self.route(self.detail_return_screen)

    def _device_progress(self, action):
        if action in {Action.BACK, Action.MENU}:
            self._back()
        elif action in {Action.PREV, Action.NEXT}:
            self.scroll = max(0, self.scroll + (1 if action is Action.NEXT else -1))

    def _back(self):
        if self.screen in {UIScreen.LINK_PROFILE, UIScreen.LINK_CONFIRM}:
            self.text_value = ""
            self.route(UIScreen.ACCOUNT)
            return
        if self.screen is UIScreen.PAIRING:
            if self.device:
                self.device.cancel_pairing()
            self.route(self.pair_return)
            return
        if self.screen is UIScreen.WIFI and self.selected_wifi:
            self.selected_wifi = None
            self.text_value = ""
            return
        parents = {
            UIScreen.PROFILE: UIScreen.PROFILE,
            UIScreen.HOME: UIScreen.PROFILE,
            UIScreen.SUBJECTS: UIScreen.HOME,
            UIScreen.INSTITUTE_WORK: UIScreen.HOME,
            UIScreen.CHAPTERS: UIScreen.SUBJECTS,
            UIScreen.PACKS: UIScreen.CHAPTERS,
            UIScreen.TEST_SETUP: UIScreen.PACKS,
            UIScreen.PROGRESS: UIScreen.HOME,
            UIScreen.SETTINGS: UIScreen.HOME,
            UIScreen.PIN: UIScreen.PROFILE,
            UIScreen.ADD_PROFILE: UIScreen.PROFILE,
            UIScreen.ASSESSMENT_MENU: UIScreen.QUESTION,
            UIScreen.LEAVE_CONFIRM: UIScreen.QUESTION,
            UIScreen.RESULT: UIScreen.HOME,
        }
        if self.screen in {UIScreen.ASSESSMENT_MENU, UIScreen.LEAVE_CONFIRM}:
            self.application.go_to_question(self.application.engine.current_index)
        if (
            self.screen in {UIScreen.DEVICE_INFO, UIScreen.DIAGNOSTICS}
            and self.diagnostic_return is UIScreen.ASSESSMENT_MENU
        ):
            self.route(UIScreen.ASSESSMENT_MENU)
            self.diagnostic_return = UIScreen.SETTINGS
            return
        self.text_value = ""
        self.route(parents.get(self.screen, UIScreen.SETTINGS))

    @property
    def keyboard_characters(self):
        if self.screen is UIScreen.LINK_PROFILE:
            return "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        if self.screen is UIScreen.PIN:
            return "1234567890"
        return (
            "abcdefghijklmnopqrstuvwxyz",
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "0123456789!@#$%^&*()-_=+[]{}:;,.?/\\'\"",
        )[self.keyboard_mode]

    def handle_text(self, value):
        if not self.student_flow:
            return
        if self.screen not in {UIScreen.PIN, UIScreen.ADD_PROFILE, UIScreen.LINK_PROFILE} and not (
            self.screen is UIScreen.WIFI and self.selected_wifi
        ):
            return
        limit = (
            12 if self.screen is UIScreen.PIN else 32 if self.screen is UIScreen.ADD_PROFILE else 63
        )
        if self.screen is UIScreen.PIN:
            value = "".join(c for c in value if c in "0123456789")
        if self.screen is UIScreen.LINK_PROFILE:
            value = "".join(c for c in value.upper() if c in self.keyboard_characters)
            limit = 10
        self.text_value = (self.text_value + value)[:limit]

    def _command(self, command):
        if command == "delete":
            self.text_value = self.text_value[:-1]
        elif command == "space":
            self.handle_text(" ")
        elif command == "case":
            self.keyboard_mode = (self.keyboard_mode + 1) % 3
            self.keyboard_index = 0
        elif command == "show":
            self.show_password = not self.show_password
        elif command == "more_keys":
            self.keyboard_index = (
                40 if self.keyboard_index < 40 and len(self.keyboard_characters) > 40 else 0
            )
        elif command == "text_submit":
            self._submit_text()
        elif command == "forgot":
            self.text_value = ""
            self.message = "PIN recovery needs your linked account online. Other authorised profiles remain usable."
        elif command == "wifi_forget" and self.selected_wifi:
            self._job("wifi_forget", name=self.selected_wifi[0])
            self.selected_wifi = None

    def _device_text(self, action):
        if action in {Action.BACK, Action.MENU}:
            self._back()
        elif action in {Action.NEXT, Action.PREV}:
            self.keyboard_index = (
                self.keyboard_index + (1 if action is Action.NEXT else -1)
            ) % len(self.keyboard_characters)
        elif action is Action.SELECT_A:
            self.handle_text(self.keyboard_characters[self.keyboard_index])
        elif action is Action.SELECT_B:
            self.text_value = self.text_value[:-1]
        elif action is Action.SELECT_C:
            self._command("case")
        elif action in {Action.CONFIRM, Action.SELECT_D}:
            self._submit_text()

    def _submit_text(self):
        if self.screen is UIScreen.LINK_PROFILE:
            if len(self.text_value) != 10:
                self.message = "Enter the 10-character code shown on the website."
                return
            self.route(UIScreen.LINK_CONFIRM)
            return
        if self.screen is UIScreen.PIN:
            success, message = self.pin_service.unlock(self.selected_profile.id, self.text_value)
            self.text_value = ""
            if success:
                self._unlocked()
            else:
                self.message = message
        elif self.screen is UIScreen.ADD_PROFILE:
            if not self.text_value.strip():
                self.message = "Enter a profile name."
                return
            self._job("account_create", create={"name": self.text_value.strip(), "exam_context": self.text_value.strip()})
            self.text_value = ""
            self.route(UIScreen.PROFILE)
        elif self.screen is UIScreen.WIFI and self.selected_wifi:
            name, saved = self.selected_wifi
            self._job("wifi_connect", ssid=name, password=self.text_value, saved=saved)
            self.text_value = ""
            self.selected_wifi = None

    def tick(self):
        if not self.device:
            return False
        changed = self.device.poll()
        if changed:
            self.message = self.device.message
            self.refresh_catalog()
            self.message = self.device.message
            if self.device.operation == "pair_poll" and self.device.credentials.load_safe() and not self.device.pairing:
                self._job("account_sync")
            elif self.device.operation in {"account_sync", "account_create"} and self.repository.get_student_account_context() and self.screen in {UIScreen.PROFILE, UIScreen.ACCOUNT, UIScreen.ADD_PROFILE, UIScreen.PAIRING}:
                self.route(UIScreen.PROFILE)
            elif self.device.operation in {"account_disconnect", "account_sync"} and not self.repository.get_student_account_context() and self.screen in {UIScreen.PROFILE, UIScreen.ACCOUNT, UIScreen.HOME, UIScreen.PAIRING}:
                self.route(UIScreen.PAIRING)
            self.focus = min(self.focus, max(0, len(self.choices) - 1))
        if (
            self.screen is UIScreen.PAIRING
            and self.device.pairing
            and not self.device.busy
            and time.monotonic() >= self.next_pair_poll
        ):
            self.next_pair_poll = time.monotonic() + 3
            self._job(
                "pair_poll",
                pairing=self.device.pairing,
                device_id=self.repository.get_or_create_device_id(),
            )
        return changed
