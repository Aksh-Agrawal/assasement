"""Quick Add Controller managing QR code generation, session status polling, and sync completion."""

import logging
import threading
from datetime import UTC, datetime
from pathlib import Path

import segno
from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot

from app.api.client import DeviceApi
from app.config import AppConfig
from app.data.repo import Repository
from app.sync.mobile_upload import (
    MobileUploadAuthError,
    MobileUploadClientError,
    MobileUploadProfileError,
    MobileUploadStorageError,
)

LOGGER = logging.getLogger(__name__)


class QuickAddController(QObject):
    statusChanged = Signal()
    qrChanged = Signal()
    timeRemainingChanged = Signal()
    resultChanged = Signal()

    # Internal thread-safe marshaling signals
    _sessionCreatedSignal = Signal(str, str, str, str, object, str)
    _sessionFailedSignal = Signal(str, str)
    _serverStatusSignal = Signal(str, object)
    _syncFinishedSignal = Signal(bool)

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

        # Connect internal cross-thread signals to main thread handlers
        self._sessionCreatedSignal.connect(self._on_session_created)
        self._sessionFailedSignal.connect(self._on_session_failed)
        self._serverStatusSignal.connect(self._handle_server_status)
        self._syncFinishedSignal.connect(self._on_sync_finished)

        # Polling & Countdown timers (run strictly on main thread)
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
    def entryUrl(self) -> str:
        if not self._upload_url:
            return ""
        from urllib.parse import urlsplit
        parsed = urlsplit(self._upload_url)
        return f"{parsed.netloc}/quick-add" if parsed.netloc else "" 

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
        self._session_id = ""
        self._short_code = ""
        self._upload_url = ""
        self._token = ""
        self._expires_at = None

        # Clean old QR file if exists
        try:
            if self._qr_file_path.is_file():
                self._qr_file_path.unlink()
        except OSError:
            pass
        self.qrChanged.emit()

        if not local_profile_id and self.app.ui_controller and self.app.ui_controller.selected_profile:
            local_profile_id = self.app.ui_controller.selected_profile.id

        self._local_profile_id = local_profile_id

        # Check device pairing / credentials upfront
        cred = self.app.credentials.load_safe() if self.app.credentials else None
        if not cred or not cred.token:
            self._status = "FAILED"
            self._status_text = "Device not linked to an account."
            self._error_message = "Connect this device to your student account in Settings > Account first."
            self.statusChanged.emit()
            return

        self._status = "CREATING"
        self._status_text = "Generating QR Code…"
        self.statusChanged.emit()

        threading.Thread(target=self._async_create_session, daemon=True).start()

    def _async_create_session(self):
        try:
            api = DeviceApi(self.config, store=self.app.credentials)
            with api.mobile_upload() as client:
                info = client.create_session(self._local_profile_id)

            # Generate QR Code using Segno (pure Python, lightweight for Pi Zero)
            qr = segno.make_qr(info.upload_url, error="m")
            self._qr_file_path.parent.mkdir(parents=True, exist_ok=True)
            qr.save(str(self._qr_file_path), scale=8, border=2)

            # Marshal success to main GUI thread via Signal
            self._sessionCreatedSignal.emit(
                info.session_id,
                info.token,
                info.upload_url,
                info.short_code,
                info.expires_at,
                info.profile_name,
            )
        except MobileUploadAuthError as err:
            LOGGER.warning("Quick add auth failure: %s (code=%s)", err, getattr(err, "code", ""))
            self._sessionFailedSignal.emit(
                "Device account not linked",
                "Connect this Raspberry Pi to your student account in Account & Devices.",
            )
        except MobileUploadProfileError as err:
            LOGGER.warning("Quick add profile failure: %s (code=%s)", err, getattr(err, "code", ""))
            self._sessionFailedSignal.emit(
                "Current profile not linked",
                "Link this study profile to your device in Account & Devices.",
            )
        except MobileUploadStorageError as err:
            LOGGER.warning("Quick add storage failure: %s (code=%s)", err, getattr(err, "code", ""))
            self._sessionFailedSignal.emit(
                "QR service unavailable",
                "QR session storage is temporarily unavailable. Please try again later.",
            )
        except MobileUploadClientError as err:
            LOGGER.warning("Quick add client failure: %s (code=%s)", err, getattr(err, "code", ""))
            if getattr(err, "code", "") == "CLOUD_UNAVAILABLE":
                self._sessionFailedSignal.emit(
                    "Cloud unavailable",
                    "Cannot reach cloud service. Check your internet connection.",
                )
            else:
                self._sessionFailedSignal.emit(
                    "Unexpected server error",
                    str(err) or "An error occurred on the server while creating the session.",
                )
        except Exception as err:
            LOGGER.error("Quick add session creation failed: %s", err)
            self._sessionFailedSignal.emit(
                "Unexpected server error",
                "Could not generate QR session. Please check connection and try again.",
            )

    def _on_session_created(self, session_id: str, token: str, upload_url: str, short_code: str, expires_at, profile_name: str):
        self._session_id = session_id
        self._token = token
        self._upload_url = upload_url
        self._short_code = short_code
        self._expires_at = expires_at
        self._profile_name = profile_name

        self._status = "WAITING_FOR_PHONE"
        self._status_text = "Waiting for phone to scan…"
        self.statusChanged.emit()
        self.qrChanged.emit()
        self.timeRemainingChanged.emit()
        self.resultChanged.emit()

        self._poll_timer.start()
        self._countdown_timer.start()

    def _on_session_failed(self, status_text: str, error_message: str):
        self._status = "FAILED"
        self._status_text = status_text
        self._error_message = error_message
        self.statusChanged.emit()
        self.qrChanged.emit()

    @Slot()
    def cancelQuickAdd(self):
        self._poll_timer.stop()
        self._countdown_timer.stop()
        sess_id = self._session_id
        if sess_id:
            def _async_cancel():
                try:
                    api = DeviceApi(self.config, store=self.app.credentials)
                    with api.mobile_upload() as client:
                        client.cancel_session(sess_id)
                except Exception:
                    pass
            threading.Thread(target=_async_cancel, daemon=True).start()

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
            self._serverStatusSignal.emit(server_status, st)
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

        self._syncFinishedSignal.emit(pack_present)

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
            # Next poll tick will retry sync
            pass
