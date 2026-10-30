"""Central Application Controller bridging device services to QML views."""

import json
import logging
import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from app.auth.credentials import CredentialStore
from app.config import AppConfig
from app.data.repo import Repository
from app.ui.controller import UIController, UIScreen
from app.ui.device import DeviceConsole
from app.ui.startup import StartupSession

LOGGER = logging.getLogger(__name__)


class AppController(QObject):
    screenChanged = Signal()
    activeProfileChanged = Signal()
    statusChanged = Signal()
    messageChanged = Signal()
    startupProgressChanged = Signal()
    keyboardVisibilityChanged = Signal()

    def __init__(self, database_path: Path, config: AppConfig = None, credentials: CredentialStore = None, parent=None):
        super().__init__(parent)
        self.database_path = Path(database_path)
        from app.connectivity import record_cloud, record_internet
        record_cloud(self.database_path, "Checking…")
        record_internet(self.database_path, "Checking…")
        self.config = config or AppConfig(database_path=self.database_path)
        self.credentials = credentials or CredentialStore(
            self.config.credential_path if self.database_path == self.config.database_path
            else self.database_path.parent / "device_credentials.json"
        )

        self._screen = "startup"
        self._screen_history = []
        self._message = ""
        self._notification_type = "info"

        # Virtual Keyboard State
        self._keyboard_visible = False
        self._keyboard_target = ""
        self._keyboard_text = ""
        self._keyboard_is_password = False
        self._keyboard_title = "Input"

        # Background connectivity scheduler state
        self._next_connectivity_check = 0.0
        self._connectivity_failures = 0
        self._initial_probe_started = False

        # Core session & device console
        self.startup_session = StartupSession(self.database_path, self.config, self.credentials)
        self.device = DeviceConsole(self.database_path, self.config, self.credentials)
        self.ui_controller: UIController | None = None
        self.repository: Repository | None = None

        # Background polling timer (100 ms)
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(100)
        self._poll_timer.timeout.connect(self._on_tick)
        self._poll_timer.start()

    # -------------------------------------------------------------------------
    # Screen & Navigation Properties
    # -------------------------------------------------------------------------
    @Property(str, notify=screenChanged)
    def screen(self) -> str:
        return self._screen

    @Property(bool, notify=screenChanged)
    def isAssessmentActive(self) -> bool:
        return self._screen in {
            "question",
            "question_detail",
            "confidence",
            "question_nav",
            "submit_confirm",
            "leave_confirm",
            "result",
            "review",
        }

    @Property(str, notify=activeProfileChanged)
    def activeProfileName(self) -> str:
        if self.ui_controller and self.ui_controller.selected_profile:
            return self.ui_controller.selected_profile.display_name
        return "Student"

    @Property(str, notify=activeProfileChanged)
    def activeProfileGrade(self) -> str:
        if self.ui_controller and self.ui_controller.selected_profile:
            cached = json.loads(self.repository.get_setting("account_profiles") or "{}")
            return next((p.get("exam_context", "") for p in cached.get("profiles", [])
                         if p["local_profile_id"] == self.ui_controller.selected_profile.id), "")
        return ""

    @Property(str, notify=statusChanged)
    def networkLabel(self) -> str:
        if self.ui_controller:
            return self.ui_controller.network_label
        return "Offline"

    @Property(bool, notify=statusChanged)
    def isOnline(self) -> bool:
        return self.networkLabel.casefold() in {"online", "syncing"}

    @Property(str, notify=statusChanged)
    def syncLabel(self) -> str:
        if self.ui_controller:
            return self.ui_controller.sync_label
        return "Offline"

    @Property(str, notify=messageChanged)
    def message(self) -> str:
        return self._message

    @Property(str, notify=messageChanged)
    def notificationType(self) -> str:
        return self._notification_type

    # -------------------------------------------------------------------------
    # Startup Check Properties
    # -------------------------------------------------------------------------
    @Property(float, notify=startupProgressChanged)
    def startupProgress(self) -> float:
        total = 8.0
        current = len(self.startup_session.rows)
        return min(1.0, current / total)

    @Property(str, notify=startupProgressChanged)
    def startupStatus(self) -> str:
        if self.startup_session.failed:
            return "Unable to start normally."
        if self.startup_session.complete:
            return "Ready!"
        if self.startup_session.rows:
            return f"{self.startup_session.rows[-1].label}: {self.startup_session.rows[-1].detail}"
        return "Preparing your learning space…"

    @Property(list, notify=startupProgressChanged)
    def startupRows(self) -> list:
        return [
            {"label": r.label, "detail": r.detail, "ok": r.ok}
            for r in self.startup_session.rows
        ]

    @Property(bool, notify=startupProgressChanged)
    def startupComplete(self) -> bool:
        return self.startup_session.complete

    @Property(bool, notify=startupProgressChanged)
    def startupFailed(self) -> bool:
        return self.startup_session.failed

    # -------------------------------------------------------------------------
    # Keyboard Properties
    # -------------------------------------------------------------------------
    @Property(bool, notify=keyboardVisibilityChanged)
    def keyboardVisible(self) -> bool:
        return self._keyboard_visible

    @Property(str, notify=keyboardVisibilityChanged)
    def keyboardText(self) -> str:
        return self._keyboard_text

    @Property(str, notify=keyboardVisibilityChanged)
    def keyboardTarget(self) -> str:
        return self._keyboard_target

    @Property(bool, notify=keyboardVisibilityChanged)
    def keyboardIsPassword(self) -> bool:
        return self._keyboard_is_password

    @Property(str, notify=keyboardVisibilityChanged)
    def keyboardTitle(self) -> str:
        return self._keyboard_title

    # -------------------------------------------------------------------------
    # Slots / Actions
    # -------------------------------------------------------------------------
    @Slot()
    def advanceStartup(self):
        if not self.startup_session.complete and not self.startup_session.failed:
            self.startup_session.advance()
            self.startupProgressChanged.emit()

            if self.startup_session.complete:
                self._initialize_runtime()

    def _initialize_runtime(self):
        try:
            self.repository = self.startup_session.repository
            self.ui_controller = UIController(self.repository, startup=True, device=self.device)
            self.ui_controller.startup_rows = tuple(self.startup_session.rows)
            self.ui_controller.finish_splash()
            self._next_connectivity_check = time.monotonic() + 0.5
            last = self.repository.get_setting("last_active_profile_id")
            for index, profile in enumerate(self.ui_controller.profiles):
                if profile.id == last:
                    self.ui_controller.profile_index = index
                    self.ui_controller.refresh_catalog()
                    break

            # Route to next appropriate screen
            if self.ui_controller.screen is UIScreen.RECOVERY:
                self.navigate("recovery")
            elif self.ui_controller.screen is UIScreen.PAIRING:
                self.navigate("pairing")
            elif self.ui_controller.screen is UIScreen.PROFILE:
                self.navigate("profile_picker")
            else:
                self.navigate("home")
            self.activeProfileChanged.emit()
            self.statusChanged.emit()
        except Exception as err:
            LOGGER.error("Failed to initialize UIController: %s", err)
            self.startup_session.failed = True
            self.startupProgressChanged.emit()
            self.navigate("recovery")

    @Slot()
    def retryStartup(self):
        self.startup_session.close()
        self.startup_session = StartupSession(self.database_path, self.config, self.credentials)
        self._screen = "startup"
        self._initial_probe_started = False
        self._next_connectivity_check = 0.0
        self.screenChanged.emit()
        self.startupProgressChanged.emit()

    @Slot(str)
    def navigate(self, target_screen: str):
        if target_screen != self._screen:
            self._screen_history.append(self._screen)
            self._screen = target_screen
            self.screenChanged.emit()

    @Slot()
    def goBack(self):
        if self._screen_history:
            prev = self._screen_history.pop()
            self._screen = prev
            self.screenChanged.emit()
        else:
            self.goHome()

    @Slot()
    def goHome(self):
        if self._screen != "home":
            self._screen_history.clear()
            self._screen = "home"
            self.screenChanged.emit()

    @Slot(str)
    def triggerAction(self, action_name: str):
        if action_name == "ACTION_BACK":
            self.goBack()
        elif action_name == "ACTION_HOME":
            self.goHome()
        elif action_name == "ACTION_POWER":
            pass

    @Slot(str, str, bool, str)
    def openKeyboard(self, target_field: str, initial_text: str, is_password: bool, title: str):
        self._keyboard_target = target_field
        self._keyboard_text = initial_text
        self._keyboard_is_password = is_password
        self._keyboard_title = title
        self._keyboard_visible = True
        self.keyboardVisibilityChanged.emit()

    @Slot(str)
    def keyboardSubmitted(self, text: str):
        self._keyboard_visible = False
        self.keyboardVisibilityChanged.emit()

    @Slot()
    def keyboardCancelled(self):
        self._keyboard_visible = False
        self.keyboardVisibilityChanged.emit()

    @Slot(str, str)
    def showNotification(self, text: str, ntype: str = "info"):
        self._message = text
        self._notification_type = ntype
        self.messageChanged.emit()

    @Slot()
    def clearMessage(self):
        self._message = ""
        self.messageChanged.emit()

    # -------------------------------------------------------------------------
    # Internal Tick
    # -------------------------------------------------------------------------
    def _on_tick(self):
        if not self.startup_session.complete and not self.startup_session.failed:
            self.advanceStartup()
            return

        # Automatic background connectivity monitor & retry schedule
        if self.startup_session.complete and not self.device.busy:
            now = time.monotonic()
            if not self._initial_probe_started:
                self._initial_probe_started = True
                self._next_connectivity_check = now + 0.5
            elif now >= self._next_connectivity_check:
                self.device.start("network")
                if self.isOnline:
                    self._connectivity_failures = 0
                    self._next_connectivity_check = now + 45.0
                else:
                    self._connectivity_failures = min(self._connectivity_failures + 1, 5)
                    self._next_connectivity_check = now + min(30.0, 5.0 * (1.5 ** self._connectivity_failures))

        revision = self.repository.content_revision() if self.repository else None
        content_updated = revision != getattr(self, "_content_revision", None)
        self._content_revision = revision

        # Poll device console for background jobs
        device_updated = self.device.poll()

        # Tick UI controller if present
        ctrl_updated = False
        if self.ui_controller:
            ctrl_updated = self.ui_controller.tick()

        if device_updated or ctrl_updated or content_updated:
            if device_updated and self.device.operation == "network":
                if self.isOnline:
                    self._connectivity_failures = 0
                    self._next_connectivity_check = time.monotonic() + 45.0
                else:
                    self._next_connectivity_check = time.monotonic() + min(
                        30.0, 5.0 * (1.5 ** getattr(self, "_connectivity_failures", 0))
                    )

            if self.ui_controller:
                self.ui_controller.refresh_catalog()
            if device_updated and self.device.operation == "account_create" and not self.device.failure:
                self.navigate("profile_picker")
            if getattr(self, "library_controller", None):
                self.library_controller.refreshLibrary()
            if self.ui_controller:
                active = getattr(self, "_active_profile_id", None)
                if active and active not in {p.id for p in self.ui_controller.profiles}:
                    self.ui_controller.application.pause()
                    from app.assessment import AssessmentApplication
                    self.ui_controller.application = AssessmentApplication(self.repository)
                    self._active_profile_id = None
                    if getattr(self, "assessment_controller", None):
                        self.assessment_controller.resetProfileState()
                    self.navigate("profile_picker")
                self.activeProfileChanged.emit()
            if getattr(self, "profile_controller", None):
                self.profile_controller.profilesChanged.emit()
            if getattr(self, "assessment_controller", None):
                self.assessment_controller.historyChanged.emit()
            self.statusChanged.emit()
            if self.device.message:
                self.showNotification(self.device.message, "info")

    def close(self):
        self._poll_timer.stop()
        if self.ui_controller:
            try:
                self.ui_controller.close()
            except Exception:
                pass
        self.startup_session.close()
