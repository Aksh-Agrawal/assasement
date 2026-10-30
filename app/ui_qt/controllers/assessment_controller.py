"""Assessment Controller driving active test taking, scoring, review, and history."""

import logging
from datetime import datetime

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from app.core.models import Confidence
from app.ui_qt.controllers.app_controller import AppController

LOGGER = logging.getLogger(__name__)


class AssessmentController(QObject):
    questionChanged = Signal()
    timerChanged = Signal()
    navigatorChanged = Signal()
    resultChanged = Signal()
    reviewChanged = Signal()
    historyChanged = Signal()

    def __init__(self, app_controller: AppController, parent=None):
        super().__init__(parent)
        self.app = app_controller
        self.app.assessment_controller = self

        self._active = False
        self._subject = ""
        self._chapter = ""
        self._timer_seconds = 0
        self._timer_enabled = False
        self._review_items = []
        self._review_filter = "all"
        self._selected_review_index = 0
        self._result_cache = None

        # Assessment timer (1 second ticks)
        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._on_timer_second)

    def resetProfileState(self):
        self._countdown_timer.stop()
        self._active = self._timer_enabled = False
        self._timer_seconds = 0
        self._subject = self._chapter = ""
        self._review_items = []
        self._result_cache = None
        self._selected_review_index = 0
        for signal in (self.questionChanged, self.timerChanged, self.navigatorChanged,
                       self.resultChanged, self.reviewChanged, self.historyChanged):
            signal.emit()

    # -------------------------------------------------------------------------
    # Active Question Properties
    # -------------------------------------------------------------------------
    @Property(bool, notify=questionChanged)
    def isActive(self) -> bool:
        return self._active

    @Property(str, notify=questionChanged)
    def subject(self) -> str:
        if self.app.ui_controller and self.app.ui_controller.selected_question_set:
            return self.app.ui_controller.selected_question_set.subject
        return self._subject or "Assessment"

    @Property(str, notify=questionChanged)
    def chapter(self) -> str:
        if self.app.ui_controller and self.app.ui_controller.selected_question_set:
            return self.app.ui_controller.selected_question_set.chapter
        return self._chapter

    @Property(int, notify=questionChanged)
    def questionIndex(self) -> int:
        if self._engine:
            return self._engine.current_index + 1
        return 1

    @Property(int, notify=questionChanged)
    def totalQuestions(self) -> int:
        if self._engine and self._engine.ordered_question_ids:
            return len(self._engine.ordered_question_ids)
        return 1

    @Property(str, notify=questionChanged)
    def questionText(self) -> str:
        if self._app_service:
            try:
                q = self._app_service.current_question()
                return q.question_text if q else ""
            except Exception:
                return ""
        return ""

    @Property(str, notify=questionChanged)
    def questionTopic(self) -> str:
        if self._app_service:
            try:
                q = self._app_service.current_question()
                return q.topic if q else ""
            except Exception:
                return ""
        return ""

    @Property(list, notify=questionChanged)
    def options(self) -> list:
        if not self._app_service:
            return []
        try:
            q = self._app_service.current_question()
            resp = self._app_service.current_response()
            sel_key = resp.selected_key if resp else None
            if not q:
                return []
            return [
                {
                    "key": opt.key,
                    "text": opt.text,
                    "selected": (opt.key == sel_key),
                }
                for opt in q.options
            ]
        except Exception:
            return []

    @Property(str, notify=questionChanged)
    def selectedKey(self) -> str:
        if self._app_service:
            try:
                resp = self._app_service.current_response()
                return resp.selected_key if resp and resp.selected_key else ""
            except Exception:
                return ""
        return ""

    @Property(bool, notify=questionChanged)
    def isMarkedForReview(self) -> bool:
        if self._app_service:
            try:
                resp = self._app_service.current_response()
                return bool(resp and resp.marked_review)
            except Exception:
                return False
        return False

    @Property(bool, notify=timerChanged)
    def timerEnabled(self) -> bool:
        return self._timer_enabled

    @Property(int, notify=timerChanged)
    def remainingSeconds(self) -> int:
        return max(0, self._timer_seconds)

    @Property(str, notify=timerChanged)
    def timerFormatted(self) -> str:
        secs = max(0, self._timer_seconds)
        mins = secs // 60
        s = secs % 60
        return f"{mins:02d}:{s:02d}"

    # -------------------------------------------------------------------------
    # Navigator & Submit Summary
    # -------------------------------------------------------------------------
    @Property(list, notify=navigatorChanged)
    def navigatorList(self) -> list:
        if not self._engine:
            return []
        res = []
        ordered_ids = self._engine.ordered_question_ids
        responses_list = self._engine.responses() if callable(self._engine.responses) else self._engine.responses
        responses = {r.question_id: r for r in responses_list}
        curr_idx = self._engine.current_index

        for idx, qid in enumerate(ordered_ids):
            resp = responses.get(qid)
            status = "unanswered"
            if resp and resp.marked_review:
                status = "flagged"
            elif resp and resp.selected_key is not None:
                status = "answered"

            res.append({
                "index": idx + 1,
                "status": status,
                "isCurrent": (idx == curr_idx),
            })
        return res

    @Property(int, notify=navigatorChanged)
    def answeredCount(self) -> int:
        if not self._engine:
            return 0
        responses_list = self._engine.responses() if callable(self._engine.responses) else self._engine.responses
        return sum(1 for resp in responses_list if resp.selected_key is not None)

    @Property(int, notify=navigatorChanged)
    def unansweredCount(self) -> int:
        if not self._engine:
            return 0
        return len(self._engine.ordered_question_ids) - self.answeredCount

    @Property(int, notify=navigatorChanged)
    def markedCount(self) -> int:
        if not self._engine:
            return 0
        responses_list = self._engine.responses() if callable(self._engine.responses) else self._engine.responses
        return sum(1 for resp in responses_list if resp.marked_review)

    # -------------------------------------------------------------------------
    # Results & Review
    # -------------------------------------------------------------------------
    @Property(int, notify=resultChanged)
    def scorePercent(self) -> int:
        if self._result_cache:
            return round(self._result_cache.percentage)
        return 0

    @Property(float, notify=resultChanged)
    def score(self) -> float:
        if self._result_cache:
            return self._result_cache.score
        return 0.0

    @Property(float, notify=resultChanged)
    def scoreMax(self) -> float:
        if self._result_cache:
            return self._result_cache.maximum
        return 0.0

    @Property(dict, notify=resultChanged)
    def confidenceBreakdown(self) -> dict:
        if not self._result_cache:
            return {"sure": 0, "notSure": 0, "guessing": 0}
        b = self._result_cache.confidence_breakdown
        return {
            "sure": b.get(Confidence.SURE, 0),
            "notSure": b.get(Confidence.NOT_SURE, 0),
            "guessing": b.get(Confidence.GUESSING, 0),
        }

    @Property(list, notify=reviewChanged)
    def reviewItems(self) -> list:
        if not self.app.ui_controller:
            return []
        items = self.app.ui_controller.review_items
        res = []
        for i, item in enumerate(items):
            sel_text = "Skipped"
            sel_key = item.response.selected_key if item.response else None
            correct_key = item.question.correct_key
            for opt in item.question.options:
                if opt.key == sel_key:
                    sel_text = f"{opt.key}: {opt.text}"
                if opt.key == correct_key:
                    corr_text = f"{opt.key}: {opt.text}"

            res.append({
                "index": i + 1,
                "position": item.position,
                "question": item.question.question_text,
                "selectedKey": sel_key or "",
                "selectedText": sel_text,
                "correctKey": correct_key,
                "correctText": corr_text,
                "isCorrect": (item.outcome == "correct"),
                "outcome": item.outcome,
                "explanation": item.question.explanation or "",
                "confidence": item.response.confidence.value if (item.response and item.response.confidence) else "unrated",
                "isFlagged": bool(item.response and item.response.marked_review),
            })
        return res

    @Property(list, notify=historyChanged)
    def historyList(self) -> list:
        if not self.app.ui_controller:
            return []
        raw_items = self.app.ui_controller.history_items
        res = []
        for it in raw_items:
            pct = 0
            if it.maximum > 0 and it.score is not None:
                pct = round((it.score / it.maximum) * 100)
            date_str = ""
            if isinstance(it.completed_at, datetime):
                date_str = it.completed_at.strftime("%d %b %Y")
            elif it.completed_at:
                date_str = str(it.completed_at)[:10]

            res.append({
                "title": it.title,
                "subject": it.subject,
                "score": it.score if it.score is not None else 0,
                "maximum": it.maximum,
                "scorePercent": pct,
                "completedAt": date_str,
                "synced": (it.sync_status.value == "SYNCED"),
                "syncStatus": it.sync_status.value,
            })
        return res

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------
    @property
    def _app_service(self):
        return self.app.ui_controller.application if self.app.ui_controller else None

    @property
    def _engine(self):
        return self._app_service.engine if self._app_service else None

    def _on_timer_second(self):
        if self._timer_seconds > 0:
            self._timer_seconds -= 1
            self.timerChanged.emit()
            if self._timer_seconds == 0:
                self._countdown_timer.stop()
                self.app.showNotification("Time is up! Submitting answers.", "warning")
                self.confirmSubmit()

    # -------------------------------------------------------------------------
    # Slots / Actions
    # -------------------------------------------------------------------------
    @Slot(str, int)
    def startTest(self, mode: str = "practice", timer_minutes: int = 0):
        if not self.app.ui_controller:
            self.app.showNotification("Application is still initializing.", "warning")
            return

        profile = self.app.ui_controller.selected_profile
        if not profile and self.app.ui_controller.profiles:
            self.app.ui_controller.profile_index = 0
            profile = self.app.ui_controller.selected_profile

        if not profile:
            self.app.showNotification("Please select a profile first.", "warning")
            return

        set_item = None
        lib_ctrl = getattr(self.app, "library_controller", None)
        target_id = getattr(lib_ctrl, "_selected_pack_id", "") if lib_ctrl else ""
        target_version = getattr(lib_ctrl, "_selected_pack_version", 1) if lib_ctrl else 1

        if target_id and self.app.repository:
            set_item = self.app.repository.get_question_set(target_id, target_version)

        if not set_item and self.app.ui_controller:
            if target_id:
                for qs in self.app.ui_controller.question_sets:
                    if qs.id == target_id and qs.version == target_version:
                        set_item = qs
                        break
            if not set_item:
                set_item = self.app.ui_controller.selected_question_set

        if not set_item:
            self.app.showNotification("No question set selected.", "warning")
            return

        try:
            profile_id = profile.id
            self._app_service.start_test(profile_id, set_item.id, set_item.version)
            self._active = True
            self._subject = set_item.subject
            self._chapter = getattr(set_item, "chapter", "") or ""

            if timer_minutes > 0:
                self._timer_enabled = True
                self._timer_seconds = timer_minutes * 60
                self._countdown_timer.start()
            else:
                self._timer_enabled = False
                self._timer_seconds = 0
                self._countdown_timer.stop()

            self.questionChanged.emit()
            self.timerChanged.emit()
            self.navigatorChanged.emit()
            self.app.navigate("question")
        except Exception as err:
            LOGGER.error("Failed to start assessment: %s", err)
            self.app.showNotification(f"Unable to start: {err}", "error")

    @Slot()
    def resumeTest(self):
        if not self.app.ui_controller:
            return
        profile = self.app.ui_controller.selected_profile
        if not profile and self.app.ui_controller.profiles:
            self.app.ui_controller.profile_index = 0
            profile = self.app.ui_controller.selected_profile
        if not profile:
            self.app.showNotification("Please select a profile first.", "warning")
            return
        try:
            if self._app_service and self._app_service.resume_attempt(profile.id):
                self._active = True
                if self.app.ui_controller.selected_question_set:
                    self._subject = self.app.ui_controller.selected_question_set.subject
                    self._chapter = getattr(self.app.ui_controller.selected_question_set, "chapter", "") or ""
                self.questionChanged.emit()
                self.timerChanged.emit()
                self.navigatorChanged.emit()
                self.app.navigate("question")
            else:
                self.app.showNotification("No in-progress test found to resume.", "info")
        except Exception:
            LOGGER.exception("Failed to resume assessment")
            self.app.showNotification("This practice session can no longer be resumed. Your completed history is safe.", "error")

    @Slot(str)
    def selectAnswer(self, key: str):
        if not self._app_service:
            return
        try:
            self._app_service.select_answer(key)
            self.questionChanged.emit()
            self.navigatorChanged.emit()
            # Open confidence prompt after selecting answer
            self.app.navigate("confidence")
        except Exception as err:
            LOGGER.error("Error selecting answer: %s", err)

    @Slot(str)
    def setConfidence(self, level: str):
        if not self._app_service:
            return
        try:
            conf_map = {
                "sure": Confidence.SURE,
                "not_sure": Confidence.NOT_SURE,
                "guessing": Confidence.GUESSING,
            }
            conf = conf_map.get(level, Confidence.UNRATED)
            self._app_service.set_confidence(conf)

            # Move to next question or submit if last
            nxt = self._app_service.next_question()
            if nxt is not None:
                self.questionChanged.emit()
                self.navigatorChanged.emit()
                self.app.navigate("question")
            else:
                self.app.navigate("submit_confirm")
        except Exception as err:
            LOGGER.error("Error setting confidence: %s", err)
            self.app.navigate("question")

    @Slot()
    def nextQuestion(self):
        if not self._app_service:
            return
        nxt = self._app_service.next_question()
        if nxt is not None:
            self.questionChanged.emit()
            self.navigatorChanged.emit()
        else:
            self.app.navigate("submit_confirm")

    @Slot()
    def previousQuestion(self):
        if not self._app_service:
            return
        try:
            self._app_service.previous_question()
            self.questionChanged.emit()
            self.navigatorChanged.emit()
        except Exception:
            pass

    @Slot()
    def toggleMarkReview(self):
        if not self._app_service:
            return
        new_state = not self.isMarkedForReview
        self._app_service.set_marked_review(new_state)
        self.questionChanged.emit()
        self.navigatorChanged.emit()

    @Slot(int)
    def goToQuestion(self, index_1_based: int):
        if not self._app_service:
            return
        try:
            self._app_service.go_to_question(index_1_based - 1)
            self.questionChanged.emit()
            self.navigatorChanged.emit()
            self.app.navigate("question")
        except Exception as err:
            LOGGER.error("Go to question failed: %s", err)

    @Slot()
    def requestSubmit(self):
        self.app.navigate("submit_confirm")

    @Slot()
    def cancelSubmit(self):
        self.app.navigate("question")

    @Slot()
    def confirmSubmit(self):
        if not self._app_service:
            return
        try:
            self._countdown_timer.stop()
            result = self._app_service.submit()
            self._result_cache = result
            self.app.ui_controller.result = result
            self._active = False

            # Prepare review items
            self.app.ui_controller._open_filtered_review("all")
            self.resultChanged.emit()
            self.reviewChanged.emit()
            self.historyChanged.emit()
            self.app.navigate("result")
        except Exception as err:
            LOGGER.error("Submit failed: %s", err)
            self.app.showNotification("Submit could not complete.", "error")

    @Slot()
    def pauseAndExit(self):
        if self._app_service:
            self._countdown_timer.stop()
            self._app_service.pause()
        self._active = False
        self.app.ui_controller.refresh_catalog()
        self.app.navigate("home")

    @Slot(str)
    def openReview(self, filter_type: str = "all"):
        self._review_filter = filter_type
        if self.app.ui_controller:
            self.app.ui_controller._open_filtered_review(filter_type)
        self.reviewChanged.emit()
        self.app.navigate("review")

    @Slot()
    def finishAndGoHome(self):
        self._active = False
        self._result_cache = None
        if self.app.ui_controller:
            self.app.ui_controller.refresh_catalog()
        self.historyChanged.emit()
        self.app.navigate("home")
