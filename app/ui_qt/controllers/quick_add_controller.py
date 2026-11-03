"""Quick Add Controller managing QR code generation, session status polling, and sync completion."""

import logging
import threading
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import segno
from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot

from app.api.client import DeviceApi
from app.config import AppConfig
from app.data.repo import Repository
from app.sync.mobile_upload import MobileUploadAuthError, MobileUploadClientError

LOGGER = logging.getLogger(__name__)


class QuickAddController(QObject):
    statusChanged = Signal()
    qrChanged = Signal()
    timeRemainingChanged = Signal()
    resultChanged = Signal()

    def __init__(self, app_controller, parent=None):
        super().__init__(parent)
        self.app = app_controller
        self.app.quick_add_controller = self

        self.database_path = Path(self.app.database_path)
        self.config: AppConfig = self.app.config

        # State
        self._status = "WAITING_FOR_PHONE"
        self._status_text = "Preparing QR session…"
        self._session_id = ""
        self._token = ""
        self._upload_url = ""
        self._short_code = ""
        self._expires_at: datetime | None = None
        self._qr_file_path = self.database_path.parent / "quick_add_qr.png"
        self._profile_name = ""
        self._pack_title = ""
        self._question_count = 0
        self._result_set_id = ""
        self._error_message = ""
        self._local_profile_id = ""

        # Polling & Countdown timers
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(2500)
        self._poll_timer.timeout.connect(self._on_poll_tick)

        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._on_countdown_tick)

        self._sync_in_progress = False

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------
    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    @Property(str, notify=statusChanged)
    def statusText(self) -> str:
        return self._status_text

    @Property(str, notify=qrChanged)
    def qrSource(self) -> str:
        if self._qr_file_path.is_file():
            return QUrl.fromLocalFile(str(self._qr_file_path)).toString()
        return ""

    @Property(str, notify=qrChanged)
    def uploadUrl(self) -> str:
        return self._upload_url

    @Property(str, notify=qrChanged)
    def shortCode(self) -> str:
        return self._short_code

    @Property(str, notify=timeRemainingChanged)
    def remainingTime(self) -> str:
        if not self._expires_at:
            return "10:00"
        now = datetime.now(UTC)
        diff = (self._expires_at - now).total_seconds()
        if diff <= 0:
            return "00:00"
        mins = int(diff // 60)
        secs = int(diff % 60)
        return f"{mins:02d}:{secs:02d}"

    @Property(str, notify=resultChanged)
    def profileName(self) -> str:
        return self._profile_name

    @Property(str, notify=resultChanged)
    def packTitle(self) -> str:
        return self._pack_title

    @Property(int, notify=resultChanged)
    def questionCount(self) -> int:
        return self._question_count

    @Property(str, notify=resultChanged)
    def resultSetId(self) -> str:
        return self._result_set_id

    @Property(str, notify=statusChanged)
    def errorMessage(self) -> str:
        return self._error_message

    # -------------------------------------------------------------------------
    # Actions / Slots
    # -------------------------------------------------------------------------
    @Slot(str)
    @Slot()
    def startQuickAdd(self, local_profile_id: str = ""):
        self._poll_timer.stop()
        self._countdown_timer.stop()
        self._sync_in_progress = False
        self._error_message = ""

        if not local_profile_id and self.app.ui_controller and self.app.ui_controller.selected_profile:
            local_profile_id = self.app.ui_controller.selected_profile.id

        self._local_profile_id = local_profile_id
        self._status = "CREATING"
        self._status_text = "Generating QR Code…"
        self.statusChanged.emit()

        threading.Thread(target=self._async_create_session, daemon=True).start()

    def _async_create_session(self):
        try:
            api = DeviceApi(self.config, store=self.app.credentials)
            with api.mobile_upload() as client:
                info = client.create_session(self._local_profile_id)

            self._session_id = info.session_id
            self._token = info.token
            self._upload_url = info.upload_url
            self._short_code = info.short_code
            self._expires_at = info.expires_at
            self._profile_name = info.profile_name

            # Generate QR Code using Segno (pure Python, lightweight for Pi Zero)
            qr = segno.make_qr(info.upload_url, error="m")
            self._qr_file_path.parent.mkdir(parents=True, exist_ok=True)
            qr.save(str(self._qr_file_path), scale=8, border=2)

            self._status = "WAITING_FOR_PHONE"
            self._status_text = "Waiting for phone to scan…"

            # Schedule UI updates and timer starts on main thread
            QTimer.singleShot(0, self._on_session_created)
        except MobileUploadAuthError as err:
            LOGGER.warning("Quick add auth failure: %s", err)
            self._status = "FAILED"
            self._status_text = "Device not linked or authenticated."
            self._error_message = "Connect this device to your student account first."
            QTimer.singleShot(0, self.statusChanged.emit)
        except Exception as err:
            LOGGER.error("Quick add session creation failed: %s", err)
            self._status = "FAILED"
            self._status_text = "Could not start session."
            self._error_message = "Check Wi-Fi connection and try again."
            QTimer.singleShot(0, self.statusChanged.emit)

    def _on_session_created(self):
        self.statusChanged.emit()
        self.qrChanged.emit()
        self.timeRemainingChanged.emit()
        self.resultChanged.emit()
        self._poll_timer.start()
        self._countdown_timer.start()

    @Slot()
    def cancelQuickAdd(self):
        self._poll_timer.stop()
        self._countdown_timer.stop()
        if self._session_id:
            try:
                api = DeviceApi(self.config, store=self.app.credentials)
                with api.mobile_upload() as client:
                    client.cancel_session(self._session_id)
            except Exception:
                pass
        self._status = "CANCELLED"
        self._status_text = "Cancelled"
        self.statusChanged.emit()
        self.app.navigate("content")

    @Slot()
    def retryQuickAdd(self):
        self.startQuickAdd(self._local_profile_id)

    @Slot()
    def practiceNow(self):
        if self._result_set_id and self.app.library_controller:
            # Select the pack and open test setup or assessment
            self.app.library_controller.selectPack(self._result_set_id, 1)
            self.app.navigate("test_setup")
        else:
            self.app.navigate("content")

    # -------------------------------------------------------------------------
    # Timer Callbacks
    # -------------------------------------------------------------------------
    def _on_countdown_tick(self):
        self.timeRemainingChanged.emit()
        if self._expires_at and datetime.now(UTC) >= self._expires_at:
            if self._status in ("WAITING_FOR_PHONE", "PHONE_CONNECTED", "UPLOADING", "PROCESSING", "NEEDS_REVIEW"):
                self._status = "EXPIRED"
                self._status_text = "This QR code has expired."
                self._poll_timer.stop()
                self._countdown_timer.stop()
                self.statusChanged.emit()

    def _on_poll_tick(self):
        if not self._session_id or self._status in ("READY", "EXPIRED", "FAILED", "CANCELLED"):
            return
        threading.Thread(target=self._async_poll_status, daemon=True).start()

    def _async_poll_status(self):
        try:
            api = DeviceApi(self.config, store=self.app.credentials)
            with api.mobile_upload() as client:
                st = client.get_status(self._session_id)

            server_status = st.status.upper()
            QTimer.singleShot(0, lambda: self._handle_server_status(server_status, st))
        except Exception as err:
            LOGGER.debug("Quick add poll transient error: %s", err)

    def _handle_server_status(self, server_status: str, st):
        if server_status == "PHONE_CONNECTED" and self._status == "WAITING_FOR_PHONE":
            self._status = "PHONE_CONNECTED"
            self._status_text = "Phone connected! Selecting questions…"
            self.statusChanged.emit()

        elif server_status == "UPLOADING":
            self._status = "UPLOADING"
            self._status_text = "Phone is uploading questions…"
            self.statusChanged.emit()

        elif server_status == "PROCESSING":
            self._status = "PROCESSING"
            self._status_text = "Analyzing questions on cloud…"
            self.statusChanged.emit()

        elif server_status == "NEEDS_REVIEW":
            self._status = "NEEDS_REVIEW"
            self._status_text = "Reviewing questions on phone…"
            self.statusChanged.emit()

        elif server_status in ("PUBLISHING", "SYNCING_TO_DEVICE", "READY", "COMPLETED"):
            self._result_set_id = st.result_set_id or self._result_set_id
            self._pack_title = st.pack_title or self._pack_title
            self._question_count = st.question_count or self._question_count
            self.resultChanged.emit()

            if not self._sync_in_progress and self._status != "READY":
                self._status = "SYNCING_TO_DEVICE"
                self._status_text = "Questions added! Syncing to this device…"
                self.statusChanged.emit()
                self._sync_in_progress = True
                threading.Thread(target=self._async_sync_and_verify, daemon=True).start()

        elif server_status == "EXPIRED":
            self._status = "EXPIRED"
            self._status_text = "This QR code has expired."
            self._poll_timer.stop()
            self._countdown_timer.stop()
            self.statusChanged.emit()

        elif server_status == "FAILED":
            self._status = "FAILED"
            self._status_text = st.error_message or "Upload processing failed."
            self._error_message = st.error_message or "Failed to process question set."
            self._poll_timer.stop()
            self.statusChanged.emit()

    def _async_sync_and_verify(self):
        """Run sync cycle to download, install, and acknowledge the newly published pack."""
        try:
            from app.sync.service import _run_cycle
            _run_cycle(self.config, heartbeat=False, refresh=True)
        except Exception as err:
            LOGGER.warning("Delivery sync cycle error: %s", err)

        # Verify pack is present in local repository
        pack_present = False
        try:
            with Repository(self.database_path) as repo:
                if self._result_set_id:
                    pk = repo.get_question_set(self._result_set_id)
                    if pk:
                        pack_present = True
                        self._pack_title = pk.title
                        self._question_count = len(pk.questions)
        except Exception:
            pass

        QTimer.singleShot(0, lambda: self._on_sync_finished(pack_present))

    def _on_sync_finished(self, pack_present: bool):
        self._sync_in_progress = False
        if pack_present:
            self._status = "READY"
            self._status_text = "Ready to practice!"
            self._poll_timer.stop()
            self._countdown_timer.stop()
            if self.app.ui_controller:
                self.app.ui_controller.refresh_catalog()
            self.statusChanged.emit()
            self.resultChanged.emit()
        else:
            # Next poll will retry sync
            pass
