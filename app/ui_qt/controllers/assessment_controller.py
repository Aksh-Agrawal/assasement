"""Assessment Controller driving active test taking, scoring, review, and history."""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from app.core.models import Confidence
from app.ui_qt.controllers.app_controller import AppController

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class CachedReviewItem:
    """Review-screen compatible view backed by profile-authorized cloud evidence."""

    position: int
    question: object
    response: object | None
    is_correct: bool | None

    @property
    def outcome(self) -> str:
        if self.response is None or self.response.selected_key is None:
            return "skipped"
        return "correct" if self.is_correct is True else "wrong"


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
        self._analytics_window = 20
        self._review_from_history = False

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
    def questionFigureSource(self) -> str:
        if not self._app_service:
            return ""
        question = self._app_service.current_question()
        reference = question.media_ref
        if not reference:
            return ""
        path = Path(self.app.config.media_directory) / reference
        return path.resolve().as_uri() if path.is_file() else ""

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
        maximum = self.scoreMax
        return round(self.score * 100 / maximum) if maximum else 0

    @Property(float, notify=resultChanged)
    def score(self) -> float:
        if self._result_cache:
            return self._result_cache.score
        return 0.0

    @Property(float, notify=resultChanged)
    def scoreMax(self) -> float:
        if self._result_cache:
            engine = self._engine
            if engine and engine.question_set and isinstance(engine.ordered_question_ids, (list, tuple)):
                return len(engine.ordered_question_ids) * engine.question_set.marking.correct
            return float(getattr(self._result_cache, "maximum", 0) or 0)
        return 0.0

    @Property(int, notify=resultChanged)
    def correctCount(self) -> int:
        value = getattr(self._result_cache, "correct", 0) if self._result_cache else 0
        return int(value) if isinstance(value, (int, float)) else 0

    @Property(int, notify=resultChanged)
    def wrongCount(self) -> int:
        value = getattr(self._result_cache, "wrong", 0) if self._result_cache else 0
        return int(value) if isinstance(value, (int, float)) else 0

    @Property(int, notify=resultChanged)
    def skippedCount(self) -> int:
        value = getattr(self._result_cache, "skipped", 0) if self._result_cache else 0
        return int(value) if isinstance(value, (int, float)) else 0

    @Property(dict, notify=resultChanged)
    def confidenceBreakdown(self) -> dict:
        if not self._result_cache:
            return {"sure": 0, "notSure": 0, "guessing": 0}
        b = getattr(self._result_cache, "confidence_totals", None)
        if b is None:
            b = getattr(self._result_cache, "confidence_breakdown", {})
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
            corr_text = ""
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
                "isSkipped": (item.outcome == "skipped"),
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
            pct = -1
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
                "synced": (it.sync_status.value == "synced"),
                "syncStatus": it.sync_status.value,
                "source": it.source,
                "correct": it.correct,
                "wrong": it.wrong,
                "skipped": it.skipped,
                "durationMs": it.duration_ms,
                "responseTimeMs": it.response_time_ms,
                "confidence": it.confidence or {},
                "answered": (getattr(it, "answered", None) if getattr(it, "answered", None) is not None
                             else it.correct + it.wrong),
                "attemptId": getattr(it, "attempt_id", None) or "",
            })
        return res

    @Property(dict, notify=historyChanged)
    def historyAnalytics(self) -> dict:
        # Match the cloud dashboard's recent-attempt analytics window. The
        # History screen remains unfiltered and retains every cached result.
        items = self.historyList[:self._analytics_window]
        correct = sum(item["correct"] for item in items)
        wrong = sum(item["wrong"] for item in items)
        skipped = sum(item["skipped"] for item in items)
        response_count = correct + wrong
        response_time = sum(item["responseTimeMs"] or 0 for item in items)
        answered_count = sum(item["answered"] for item in items)
        levels = ("sure", "not_sure", "guessing", "unrated")
        confidence = {
            level: {"correct": 0, "wrong": 0}
            for level in levels
        }
        for item in items:
            for level in levels:
                counts = item.get("confidence", {}).get(level, {})
                confidence[level]["correct"] += int(counts.get("correct", 0))
                confidence[level]["wrong"] += int(counts.get("wrong", 0))

        trends = []
        for index, item in enumerate(reversed(items)):
            graded = item["correct"] + item["wrong"]
            trends.append({
                "index": index,
                "label": item["completedAt"],
                "accuracyPercent": round(item["correct"] * 100 / graded) if graded else -1,
                "correct": item["correct"],
                "wrong": item["wrong"],
            })
        return {
            "attempts": len(items),
            "correct": correct,
            "wrong": wrong,
            "skipped": skipped,
            "accuracyPercent": round(correct * 100 / response_count) if response_count else -1,
            "practiceTimeMs": sum(item["durationMs"] for item in items),
            "averageResponseTimeMs": round(response_time / answered_count) if answered_count else -1,
            "webAttempts": sum(item["source"] == "web" for item in items),
            "deviceAttempts": sum(item["source"] == "device" for item in items),
            "confidence": confidence,
            "trends": trends,
        }

    @Property(int, notify=historyChanged)
    def analyticsWindow(self) -> int:
        return self._analytics_window

    @Slot(int)
    def setAnalyticsWindow(self, count: int):
        if count in (5, 10, 20) and count != self._analytics_window:
            self._analytics_window = count
            self.historyChanged.emit()

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
    @Slot(str, int, int, str, str, bool)
    def startTest(self, mode: str = "practice", timer_minutes: int = 0, question_count: int = 0, difficulty: str = "", topic: str = "", shuffle: bool = False):
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
            self._app_service.start_test(
                profile_id, set_item.id, set_item.version,
                question_count=question_count or None,
                difficulty=difficulty or None,
                topic=topic or None,
                shuffle=shuffle,
            )
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
        self._review_from_history = False
        self._review_filter = filter_type
        if self.app.ui_controller:
            self.app.ui_controller._open_filtered_review(filter_type)
        self.reviewChanged.emit()
        self.app.navigate("review")

    @Slot(str)
    def openHistoryReview(self, attempt_id: str):
        """Open local Pi evidence or an authorized cloud review cached in SQLite."""
        ui = self.app.ui_controller
        repository = self.app.startup_session.repository if self.app.startup_session else None
        attempt = repository.get_attempt(attempt_id) if repository and attempt_id else None
        profile = ui.selected_profile if ui else None
        if profile is None:
            return
        if attempt is None or attempt.profile_id != profile.id:
            cloud_item = next((item for item in repository.completed_results(profile.id)
                               if item.get("attempt_id") == attempt_id), None) if repository else None
            if not cloud_item or not cloud_item.get("review_available") or not cloud_item.get("review"):
                self.app.showNotification(
                    "Detailed review is not available for this assessment on this device.", "info"
                )
                return
            self._open_cached_history_review(cloud_item)
            return
        question_set = repository.get_question_set(attempt.set_id, attempt.set_version)
        order = repository.get_attempt_question_order(attempt.id)
        if question_set is None or not order:
            self.app.showNotification(
                "Question details for this assessment are no longer on this device.", "warning"
            )
            return
        from app.core.engine import ReviewItem

        questions = {question.id: question for question in question_set.questions}
        responses = {
            response.question_id: response
            for response in repository.get_attempt_responses(attempt.id)
        }
        ui.review_items = tuple(
            ReviewItem(position, questions[question_id], responses.get(question_id))
            for position, question_id in enumerate(order, start=1)
            if question_id in questions
        )
        self._review_items = list(ui.review_items)
        self._review_filter = "all"
        self._review_from_history = True
        self._selected_review_index = 0
        self.reviewChanged.emit()
        self.app.navigate("review")

    def _open_cached_history_review(self, attempt: dict) -> None:
        from app.core.models import Confidence

        review_items = []
        for position, evidence in enumerate(attempt["review"], start=1):
            options = tuple(SimpleNamespace(key=option["key"], text=option["text"])
                            for option in evidence.get("options", []))
            question = SimpleNamespace(
                id=evidence["question_id"],
                question_text=evidence.get("question_text") or "Question text unavailable",
                options=options,
                correct_key=evidence.get("correct_key"),
                explanation=evidence.get("explanation") or "",
            )
            selected_key = evidence.get("selected_key")
            confidence_value = evidence.get("confidence")
            response = None if selected_key is None else SimpleNamespace(
                selected_key=selected_key,
                confidence=Confidence(confidence_value) if confidence_value else Confidence.UNRATED,
                marked_review=bool(evidence.get("marked_review", False)),
            )
            review_items.append(CachedReviewItem(
                position, question, response, evidence.get("is_correct")
            ))
        ui = self.app.ui_controller
        ui.review_items = tuple(review_items)
        self._review_items = review_items
        self._review_filter = "all"
        self._review_from_history = True
        self._selected_review_index = 0
        self.reviewChanged.emit()
        self.app.navigate("review")

    @Slot()
    def closeReview(self):
        self.app.navigate("history" if self._review_from_history else "result")
        self._review_from_history = False

    @Slot()
    def finishAndGoHome(self):
        self._active = False
        self._result_cache = None
        if self.app.ui_controller:
            self.app.ui_controller.refresh_catalog()
        self.historyChanged.emit()
        self.app.navigate("home")
