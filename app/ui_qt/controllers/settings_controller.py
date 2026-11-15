"""Settings Controller managing Wi-Fi, Sync, Account Pairing, Updates, and Diagnostics."""

import json
import os
import shutil
import stat
from datetime import UTC, datetime
from time import monotonic, time

from packaging.version import Version
from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from app.connectivity import (
    cloud_state,
    internet_label,
    wifi_state,
)
from app.ui_qt.controllers.app_controller import AppController
from app.update.layout import active_release_version

UPDATE_OPERATIONS = {
    "update_check": "Checking for updates",
    "update_download": "Downloading update",
    "update_install": "Starting installation",
}
UPDATE_PREPARATION = {
    "downloading": "Downloading update",
    "verifying": "Verifying update",
    "checking_archive": "Checking archive contents",
    "extracting": "Preparing installation",
    "finalizing": "Finalizing preparation",
}
UPDATE_INSTALLATION = {
    "checking_release": "Checking release files",
    "unpacking_release": "Unpacking release files",
    "installing_dependencies": "Installing dependencies",
    "checking_saved_data": "Checking saved data compatibility",
    "testing_startup": "Testing app startup",
    "activating_release": "Activating the update",
}
UPDATE_PROGRESS_LABELS = {"downloading": "Downloaded", "verifying": "File checked", "extracting": "Extracted"}
UPDATE_CHECK_INTERVAL = 24 * 60 * 60
LAST_UPDATE_CHECK_KEY = "last_software_update_check"
REMEMBERED_UPDATE_KEY = "remembered_software_update"
DISMISSED_UPDATE_KEY = "dismissed_software_update"


class SettingsController(QObject):
    wifiChanged = Signal()
    syncChanged = Signal()
    accountChanged = Signal()
    storageChanged = Signal()
    updateChanged = Signal()
    diagnosticsChanged = Signal()
    instituteChanged = Signal()

    def __init__(self, app_controller: AppController, parent=None):
        super().__init__(parent)
        self.app = app_controller
        self.app.statusChanged.connect(self.wifiChanged.emit)
        self.app.statusChanged.connect(self.syncChanged.emit)
        self.app.statusChanged.connect(self.diagnosticsChanged.emit)
        self.app.statusChanged.connect(self.accountChanged.emit)
        self.app.activeProfileChanged.connect(self.accountChanged.emit)
        self.app.activeProfileChanged.connect(self.instituteChanged.emit)
        self.app.activeProfileChanged.connect(self.storageChanged.emit)
        self._sync_countdown = QTimer(self)
        self._sync_countdown.setInterval(1000)
        self._sync_countdown.timeout.connect(self.syncChanged.emit)
        self._sync_countdown.start()
        self._diagnostics_data = None
        self._unlink_start_error = ""
        self._running_version = Version(self.app.config.application_version)
        self._active_version = None
        self._release_status_path = self.app.config.update_root / "status.json"
        self._release_status_revision = None
        self._ignored_status_revision = None
        self._release_state = ""
        self._release_step = ""
        self._update_requested = False
        self._update_error = ""
        self._checked_for_update = False
        self._install_deferred = False
        self._update_view = None
        self._next_update_poll = 0.0
        self._last_update_check = None
        self._update_settings_repository = None
        self._remembered_update = ""
        self._dismissed_update = ""
        self.app.deviceOperationFinished.connect(self._updateOperationFinished)
        self._update_timer = QTimer(self)
        self._update_timer.setInterval(250)
        self._update_timer.timeout.connect(self._pollUpdateState)
        self._update_timer.start()
        self.refreshUpdateState()

    # -------------------------------------------------------------------------
    # Wi-Fi & Network Properties
    # -------------------------------------------------------------------------
    @Property(bool, notify=wifiChanged)
    def isWifiConnected(self) -> bool:
        if self.app.device and self.app.device.wifi_connected:
            return True
        if self.app.repository:
            return wifi_state(self.app.repository).get("state") == "connected"
        return False

    @Property(bool, notify=wifiChanged)
    def isScanning(self) -> bool:
        return bool(
            self.app.device
            and self.app.device.busy
            and self.app.device.operation == "wifi_scan"
        )

    @Property(bool, notify=wifiChanged)
    def isConnecting(self) -> bool:
        return bool(
            self.app.device
            and self.app.device.busy
            and self.app.device.operation == "wifi_connect"
        )

    @Property(str, notify=wifiChanged)
    def connectedSsid(self) -> str:
        if not self.isWifiConnected:
            return "Not connected"
        if self.app.device and getattr(self.app.device, "connected_ssid", None):
            return self.app.device.connected_ssid
        if self.app.repository:
            ssid = wifi_state(self.app.repository).get("ssid")
            if ssid:
                return ssid
        if self.app.device and self.app.device.saved_networks:
            return self.app.device.saved_networks[0]
        return "Connected"

    @Property(str, notify=wifiChanged)
    def internetStatus(self) -> str:
        if self.app.repository:
            lbl = internet_label(self.app.repository)
            if lbl != "Checking…":
                return lbl
        if self.app.device and self.app.device.internet_status not in {"Unknown", ""}:
            return self.app.device.internet_status
        return "Available" if self.app.isOnline else "Unavailable"

    @Property(str, notify=wifiChanged)
    def cloudStatus(self) -> str:
        return self.app.networkLabel

    @Property(list, notify=wifiChanged)
    def availableNetworks(self) -> list:
        if not self.app.device or not self.app.device.networks:
            # If on non-Linux development platform without nmcli, provide realistic samples
            has_nmcli = (
                self.app.device.wifi.available
                if (self.app.device and hasattr(self.app.device, "wifi"))
                else (shutil.which("nmcli") is not None)
            )
            if not has_nmcli:
                return [
                    {"ssid": "StudyBuddy-Home", "connected": True, "saved": True, "signal": 90, "encrypted": True},
                    {"ssid": "HomeWiFi", "connected": False, "saved": False, "signal": 75, "encrypted": True},
                    {"ssid": "SchoolWiFi", "connected": False, "saved": False, "signal": 60, "encrypted": True},
                    {"ssid": "Library-Guest", "connected": False, "saved": False, "signal": 40, "encrypted": False},
                ]
            return []

        saved = set(self.app.device.saved_networks or ())
        active_ssid = self.connectedSsid
        res = []
        for n in self.app.device.networks:
            ssid = getattr(n, "ssid", str(n))
            if not ssid:
                continue
            is_active = (ssid == active_ssid and self.isWifiConnected) or getattr(n, "connected", False)
            res.append({
                "ssid": ssid,
                "connected": is_active,
                "saved": (ssid in saved) or getattr(n, "saved", False),
                "signal": getattr(n, "signal_percent", 70),
                "encrypted": getattr(n, "encrypted", True),
            })
        return res

    # -------------------------------------------------------------------------
    # Sync Properties
    # -------------------------------------------------------------------------
    @Property(bool, notify=syncChanged)
    def automaticSync(self):
        return not self.app.repository or self.app.repository.get_setting("automatic_sync") != "0"

    @Slot(bool)
    def setAutomaticSync(self, enabled):
        if self.app.repository:
            self.app.repository.set_setting("automatic_sync", "1" if enabled else "0")
        self.syncChanged.emit()

    @Property(str, notify=syncChanged)
    def nextAutomaticSync(self):
        if not self.automaticSync:
            return "Off"
        value = self.app.repository.get_setting("next_automatic_sync") if self.app.repository else None
        try:
            seconds = max(0, int((datetime.fromisoformat(value) - datetime.now(UTC)).total_seconds()))
            return f"In {seconds} seconds" if seconds else "Due now"
        except (TypeError, ValueError):
            return "Starting…"

    @Property(bool, notify=syncChanged)
    def isSyncing(self) -> bool:
        device = self.app.device
        return bool((device and device.busy and device.operation == "sync") or self.app.syncLabel == "Syncing")

    @Property(str, notify=syncChanged)
    def lastSyncTime(self) -> str:
        value = self.app.repository.get_setting("last_full_sync_success") if self.app.repository else None
        if not value:
            return "Never"
        try:
            elapsed = max(0, int((datetime.now(UTC) - datetime.fromisoformat(value)).total_seconds()))
            if elapsed < 60:
                return "Just now"
            if elapsed < 3600:
                return f"{elapsed // 60} minutes ago"
            return datetime.fromisoformat(value).strftime("%d %b %H:%M")
        except (TypeError, ValueError):
            return "Never"

    @Property(int, notify=syncChanged)
    def pendingAttemptsCount(self) -> int:
        if self.app.ui_controller:
            return self.app.ui_controller.pending_sync_count
        return 0

    @Property(str, notify=syncChanged)
    def syncStatusSummary(self) -> str:
        if self.app.ui_controller:
            return self.app.ui_controller.sync_label
        return "Offline"

    @Property(str, notify=syncChanged)
    def syncDetail(self) -> str:
        pending = self.pendingAttemptsCount
        full = {}
        if self.app.repository:
            try:
                full = json.loads(self.app.repository.get_setting("last_full_sync") or "{}")
            except (TypeError, ValueError):
                full = {}
        result = full.get("result")
        stages = full.get("stages", {})
        history = full.get("history", {})
        content = full.get("content", {})
        upload = stages.get("attempt_uploads", {}) if isinstance(stages, dict) else {}
        if result == "Authentication required":
            return "Reconnect this device to your account before syncing. Your local assessments are safe."
        if result in {"Failed", "Partially synced"}:
            failed = upload.get("failed", 0) if isinstance(upload, dict) else 0
            messages = []
            if failed:
                messages.append(f"{failed} assessment upload(s) need a retry.")
            if history.get("review_failures") and not history.get("failures"):
                messages.append("History was updated. Some answer reviews need a retry.")
            elif stages.get("history") not in {None, "OK", "Not checked"}:
                messages.append("History download needs a retry.")
            if stages.get("content") == "Delivery reconciliation failed":
                messages.append("Some Practice downloads need a retry.")
            detail = " ".join(messages) or "Some cloud updates could not be downloaded."
            return f"Last sync was incomplete. {detail} Local records remain saved."
        if pending:
            return f"{pending} completed assessment(s) are saved on this device and waiting to sync."
        if result == "Up to date":
            if content.get("remaining"):
                return "History is up to date. More Practice packs are waiting to download."
            if not history.get("profiles_synced", 1):
                return "No linked Study Profiles were available to sync."
            return "History, Analytics, and Practice downloads are up to date."
        return "Your assessments stay saved offline and sync when the device reconnects."

    # -------------------------------------------------------------------------
    # Account & Pairing Properties
    # -------------------------------------------------------------------------
    @Property(bool, notify=accountChanged)
    def isPaired(self) -> bool:
        if self.app.credentials:
            return bool(self.app.credentials.load_safe())
        return False

    @Property(str, notify=accountChanged)
    def accountName(self) -> str:
        if self.app.repository:
            ctx = self.app.repository.get_student_account_context()
            if ctx:
                return ctx["display_name"]
        return "Not connected"

    @Property(bool, notify=accountChanged)
    def hasAccount(self) -> bool:
        return bool(self.app.repository and self.app.repository.get_student_account_context())

    @Property(str, notify=accountChanged)
    def accountStatus(self) -> str:
        if not self.app.repository:
            return "Not connected"
        from app.auth.product_state import account_status
        label = account_status(self.app.repository, verified_this_run=self.app.device.account_verified)
        return label.partition(" - ")[0]

    @Property(bool, notify=accountChanged)
    def accountActionBusy(self) -> bool:
        return bool(self.app.device and self.app.device.busy)

    @Property(bool, notify=accountChanged)
    def unlinkPending(self) -> bool:
        return bool(self.app.repository and self.app.repository.get_setting("pending_unlink"))

    @Property(str, notify=accountChanged)
    def unlinkStatus(self) -> str:
        device = self.app.device
        if device and device.busy and device.operation in {"account_disconnect", "profile_unlink", "unlink_retry"}:
            return device.message
        if self.unlinkPending:
            pending = json.loads(self.app.repository.get_setting("pending_unlink") or "{}")
            target = "Account" if pending.get("scope") == "account" else "Study Profile"
            return f"{target} unlink pending. It will retry when connected."
        if self._unlink_start_error:
            return self._unlink_start_error
        return (self.app.repository.get_setting("unlink_message") or "") if self.app.repository else ""

    @Property(str, notify=accountChanged)
    def pairingCode(self) -> str:
        if self.app.device and self.app.device.pairing:
            return getattr(self.app.device.pairing, "code", "")
        return ""

    @Property(str, notify=accountChanged)
    def pairingStatus(self) -> str:
        device = self.app.device
        if device and device.busy:
            if device.operation == "pair_request":
                return "Generating a pairing code…"
            if device.operation == "account_sync":
                return "Loading your Study Profiles…"
        if self.pairingError:
            return self.pairingError
        if self.pairingCode:
            return "Waiting for you to confirm on the learning portal."
        return "Generate a code to connect your account."

    @Property(str, notify=accountChanged)
    def pairingError(self) -> str:
        return self.app.device.pairing_error if self.app.device else ""

    @Property(bool, notify=accountChanged)
    def canRetryAccountSync(self) -> bool:
        return bool(self.isPaired and not self.hasAccount and self.app.repository
                    and self.app.repository.get_setting("account_connection_state") != "revoked")

    # -------------------------------------------------------------------------
    # Storage & Content Properties
    # -------------------------------------------------------------------------
    @Property(float, notify=storageChanged)
    def storageUsedGb(self) -> float:
        try:
            total, used, free = shutil.disk_usage(".")
            return round(used / (1024 ** 3), 1)
        except Exception:
            return 12.5

    @Property(float, notify=storageChanged)
    def storageTotalGb(self) -> float:
        try:
            total, used, free = shutil.disk_usage(".")
            return round(total / (1024 ** 3), 1)
        except Exception:
            return 29.0

    @Property(int, notify=storageChanged)
    def storagePercent(self) -> int:
        tot = self.storageTotalGb
        if tot > 0:
            return round((self.storageUsedGb / tot) * 100)
        return 43

    @Property(list, notify=storageChanged)
    def installedPacks(self) -> list:
        if not self.app.ui_controller:
            return []
        res = []
        for p in self.app.ui_controller.question_sets:
            res.append({
                "id": p.id,
                "version": p.version,
                "title": p.title,
                "subject": p.subject,
                "chapter": p.chapter,
                "questionCount": len(p.questions),
                "isInstalled": True,
            })
        return res

    # -------------------------------------------------------------------------
    # Software Update Properties
    # -------------------------------------------------------------------------
    @Property(str, notify=updateChanged)
    def appVersion(self) -> str:
        # A symlink switch cannot change which Python code this process imported.
        return str(self._running_version)

    @Property(str, notify=updateChanged)
    def activeReleaseVersion(self) -> str:
        return str(self._active_version) if self._active_version is not None else ""

    @property
    def _restart_required(self) -> bool:
        return self._active_version is not None and self._active_version != self._running_version

    def _availableUpdate(self):
        update = getattr(self.app.device, "available_update", None)
        installed = self._active_version or self._running_version
        if not self._restart_required and update and update.manifest.version > installed:
            return update
        return None

    @Property(bool, notify=updateChanged)
    def hasUpdate(self) -> bool:
        return self._availableUpdate() is not None

    @Property(str, notify=updateChanged)
    def updateVersion(self) -> str:
        update = self._availableUpdate()
        return str(update.manifest.version) if update else ""

    @Property(str, notify=updateChanged)
    def availableVersion(self) -> str:
        return self.updateVersion

    @Property(str, notify=updateChanged)
    def updateReminderVersion(self) -> str:
        if self._restart_required or self.updatePendingInstall:
            return ""
        if self.hasUpdate:
            return self.availableVersion if self.updateCompatible else ""
        return self._remembered_update

    @Property(str, notify=updateChanged)
    def updateNoticeVersion(self) -> str:
        version = self.updateReminderVersion
        return version if version != self._dismissed_update else ""

    @Property(str, notify=updateChanged)
    def updateNotes(self) -> str:
        update = self._availableUpdate()
        return update.manifest.data["release"].get("notes", "") if update else ""

    @Property(str, notify=updateChanged)
    def updateError(self) -> str:
        return self._update_error

    @Property(dict, notify=updateChanged)
    def updateWork(self) -> dict:
        device = self.app.device
        if device and device.busy and device.operation == "update_download":
            phase, fraction = device.update_work
            if fraction is None:
                return {"label": "In progress", "indeterminate": True, "fraction": 0.0}
            label = UPDATE_PROGRESS_LABELS[phase]
            return {"label": f"{label} · {int(fraction * 100)}%", "indeterminate": False, "fraction": fraction}
        if self._release_state == "installing" and self._release_step:
            completed = tuple(UPDATE_INSTALLATION).index(self._release_step)
            total = len(UPDATE_INSTALLATION)
            return {"label": f"{completed} of {total} installation steps complete", "indeterminate": False,
                    "fraction": completed / total}
        if (self._update_requested or self._release_state == "installing"
                or (device and device.busy and device.operation == "update_install")):
            return {"label": "In progress", "indeterminate": True, "fraction": 0.0}
        return {}

    @Property(bool, notify=updateChanged)
    def updateBusy(self) -> bool:
        device = self.app.device
        return bool((device and device.busy and device.operation in UPDATE_OPERATIONS)
                    or self._update_requested or self._release_state == "installing")

    @Property(bool, notify=updateChanged)
    def updateCompatible(self) -> bool:
        update = self._availableUpdate()
        if not update or not self.app.repository:
            return False
        try:
            return (
                update.manifest.data["compatibility"] == {
                    "platform": self.app.config.update_platform,
                    "architecture": self.app.config.update_architecture,
                }
                and update.manifest.data["release"]["required_db_schema"] <= self.app.repository.schema_version
                and self._running_version >= Version(update.manifest.data["release"]["min_supported_version"])
            )
        except (KeyError, ValueError):
            return False

    @Property(bool, notify=updateChanged)
    def updatePendingInstall(self) -> bool:
        return self._install_deferred or self._update_requested or self._release_state == "installing"

    @Property(str, notify=updateChanged)
    def updateStatus(self) -> str:
        device = self.app.device
        if device and device.busy and device.operation == "update_download":
            return UPDATE_PREPARATION[device.update_work[0]]
        if self._release_state == "installing":
            return UPDATE_INSTALLATION.get(self._release_step, "Installing update")
        if device and device.busy and device.operation in UPDATE_OPERATIONS:
            return UPDATE_OPERATIONS[device.operation]
        if self._update_requested:
            return "Starting installation"
        if self._restart_required:
            return "Restart required to load the active release"
        if self._update_error:
            return "Update failed. Try again"
        if self._release_state == "rolled_back":
            return "Update failed. Previous version restored"
        if self._release_state == "failed":
            return "Update failed. Try again"
        if self._install_deferred:
            return "Ready to install after this assessment"
        if self.hasUpdate:
            return "New version available"
        if self.updateReminderVersion:
            return "Check online for the available update"
        if self._checked_for_update or self._active_version or self._release_state == "successful":
            return "Software is up to date"
        return "Check for a software update"

    def _pollUpdateState(self):
        if (self.app.screen == "software_update" or self.updatePendingInstall
                or self.app.repository is not self._update_settings_repository):
            self.refreshUpdateState()
        now = monotonic()
        if now < self._next_update_poll:
            return
        self._next_update_poll = now + 5
        if self._last_update_check is not None and time() < self._last_update_check + UPDATE_CHECK_INTERVAL:
            return
        device = self.app.device
        if (not self.app.startupComplete or not self.app.repository or not device or device.busy
                or self.app.isAssessmentActive or self.app.keyboardVisible or self.updatePendingInstall
                or not self.app.config.api_base_url or not self.app.isOnline or not device.credentials.load_safe()):
            return
        self.refreshUpdateState()
        if not self.updateBusy and not self.updatePendingInstall and not self._restart_required:
            device.start("update_check", automatic=True)
            if device.busy:
                self._recordUpdateCheck()
            self.refreshUpdateState()

    def _loadUpdateSettings(self):
        repository = self.app.repository
        if repository is self._update_settings_repository:
            return
        self._update_settings_repository = repository
        self._last_update_check = None
        self._remembered_update = self._dismissed_update = ""
        if repository:
            self._remembered_update = repository.get_setting(REMEMBERED_UPDATE_KEY) or ""
            self._dismissed_update = repository.get_setting(DISMISSED_UPDATE_KEY) or ""
            last_check = repository.get_setting(LAST_UPDATE_CHECK_KEY)
            if last_check:
                try:
                    self._last_update_check = float(last_check)
                except (TypeError, ValueError):
                    pass

    def _recordUpdateCheck(self):
        self._last_update_check = time()
        if self.app.repository:
            self.app.repository.set_setting(LAST_UPDATE_CHECK_KEY, str(self._last_update_check))

    @Slot()
    def dismissUpdateNotice(self):
        version = self.updateNoticeVersion
        if version:
            self._dismissed_update = version
            if self.app.repository:
                self.app.repository.set_setting(DISMISSED_UPDATE_KEY, version)
            self.refreshUpdateState()

    @Slot()
    def viewUpdateNotice(self):
        self.dismissUpdateNotice()
        self.app.navigate("software_update")

    @Slot()
    def refreshUpdateState(self):
        self._active_version = active_release_version()
        self._loadUpdateSettings()
        try:
            if self._remembered_update and Version(self._remembered_update) <= (self._active_version or self._running_version):
                self._remembered_update = ""
        except (TypeError, ValueError):
            self._remembered_update = ""
        self._refreshReleaseStatus()
        self._update_requested = (
            self._release_state not in {"successful", "failed", "rolled_back"}
            and (self.app.config.update_inbox / "request.json").is_file()
        )
        device = self.app.device
        if self._install_deferred and device and not device.busy and not self.app.isAssessmentActive:
            self._install_deferred = False
            if (not self.updatePendingInstall and device.staged
                    and self.updateCompatible and device.staged.name == self.availableVersion):
                device.start("update_install", staged=str(device.staged))
        view = (self.appVersion, self.activeReleaseVersion, self.availableVersion,
                self.updateNotes, self.updateCompatible,
                self.updateStatus, self.updateError, self.updateBusy,
                self.updateWork, self.updatePendingInstall, self.updateReminderVersion, self.updateNoticeVersion)
        if view != self._update_view:
            self._update_view = view
            self.updateChanged.emit()

    @Slot(str)
    def _updateOperationFinished(self, operation):
        if operation not in UPDATE_OPERATIONS:
            return
        device = self.app.device
        if operation == "update_check":
            if not device.failure:
                self._checked_for_update = True
                self._update_error = ""
                version = self.availableVersion if self.updateCompatible else ""
                if version != self._remembered_update:
                    self._remembered_update = version
                    if self.app.repository:
                        self.app.repository.set_setting(REMEMBERED_UPDATE_KEY, version)
            elif not device.update_check_automatic:
                self._update_error = device.message
        elif device.failure:
            self._update_error = device.message
            self._install_deferred = False
        elif operation == "update_download":
            self._install_deferred = True
        self.refreshUpdateState()

    def _refreshReleaseStatus(self):
        self._release_state = ""
        self._release_step = ""
        self._release_status_revision = None
        try:
            if not stat.S_ISREG(self._release_status_path.lstat().st_mode):
                return
            with self._release_status_path.open(encoding="utf-8") as status:
                info = os.fstat(status.fileno())
                self._release_status_revision = (info.st_ino, info.st_mtime_ns, info.st_ctime_ns)
                if info.st_size > 4096 or self._release_status_revision == self._ignored_status_revision:
                    return
                data = json.load(status)
            if not isinstance(data, dict):
                return
            state = data.get("state")
            version_text = data.get("version")
            version = Version(version_text) if isinstance(version_text, str) and version_text else None
        except (OSError, ValueError):
            return
        installed = self._active_version or self._running_version
        if state == "successful" and version == installed:
            self._release_state = state
            self._update_error = ""
        elif state == "installing" and version is not None and version >= installed:
            self._release_state = state
            step = data.get("step")
            if isinstance(step, str) and step in UPDATE_INSTALLATION:
                self._release_step = step
        elif state == "failed" and (version_text == "" or (version is not None and version > installed)):
            self._release_state = state
        elif state == "rolled_back" and version is not None and version > installed:
            self._release_state = state

    # -------------------------------------------------------------------------
    # Diagnostics Properties
    # -------------------------------------------------------------------------
    @Property(str, notify=diagnosticsChanged)
    def apiBaseUrl(self) -> str:
        if self.app.config and self.app.config.api_base_url:
            return self.app.config.api_base_url
        return "https://startup-cloud.onrender.com"

    @Property(str, notify=diagnosticsChanged)
    def overallHealth(self) -> str:
        return self.app.networkLabel

    @Property(str, notify=diagnosticsChanged)
    def deviceId(self) -> str:
        if self.app.repository:
            return self.app.repository.get_or_create_device_id()
        return "rpi-zero2w-studybuddy-01"

    @Property(list, notify=diagnosticsChanged)
    def diagnosticItems(self) -> list:
        nm_available = (
            self.app.device.wifi.available
            if (self.app.device and hasattr(self.app.device, "wifi"))
            else (shutil.which("nmcli") is not None)
        )
        nm_str = "OK" if nm_available else "Unavailable"
        wifi_str = "Connected" if self.isWifiConnected else "Disconnected"
        ssid_str = self.connectedSsid if self.isWifiConnected else "None"
        inet_str = self.internetStatus
        cloud_str = self.cloudStatus

        net = getattr(self.app.device, "network", None) if self.app.device else None
        if net and net.checked:
            cloud_health = "OK" if net.backend_reachable else "Failed"
            cloud_ready = "OK" if net.database_ready else ("Not ready" if net.backend_reachable else "Unavailable")
        elif cloud_str == "Online":
            cloud_health = "OK"
            cloud_ready = "OK"
        elif cloud_str == "Server unavailable":
            cloud_health = "OK"
            cloud_ready = "Not ready"
        elif cloud_str == "Offline":
            cloud_health = "Failed"
            cloud_ready = "Unavailable"
        else:
            cloud_health = "Not checked"
            cloud_ready = "Not checked"

        auth_str = ("Action required" if not self.isPaired or cloud_str == "Authentication required"
                    else "OK" if cloud_str == "Online" else "Unverified")
        last_cloud = "Never"
        if self.app.repository:
            c_info = cloud_state(self.app.repository)
            lcs = c_info.get("last_cloud_success")
            if lcs:
                try:
                    dt = datetime.fromisoformat(lcs)
                    elapsed = int((datetime.now(UTC) - dt).total_seconds())
                    if elapsed < 60:
                        last_cloud = "Just now"
                    elif elapsed < 3600:
                        last_cloud = f"{elapsed // 60}m ago"
                    else:
                        last_cloud = dt.strftime("%d %b %H:%M")
                except Exception:
                    last_cloud = lcs[:19]

        items = [
            {"name": "NetworkManager", "detail": f"Subprocess networking backend: {nm_str}", "status": nm_str},
            {"name": "Wi-Fi Association", "detail": f"State: {wifi_str} • SSID: {ssid_str}", "status": wifi_str},
            {"name": "IP Assignment", "detail": "Kernel networking & dual-stack interface ready", "status": "Assigned" if self.isWifiConnected else "Unassigned"},
            {"name": "DNS Resolution", "detail": "System DNS resolver functional", "status": "OK" if inet_str == "Available" else "Checking…"},
            {"name": "Internet Reachability", "detail": f"Global internet routing: {inet_str}", "status": inet_str},
            {"name": "Cloud Health (/health)", "detail": f"API base: {self.apiBaseUrl} • Status: {cloud_health}", "status": cloud_health},
            {"name": "Cloud Readiness (/ready)", "detail": f"Database & migration readiness: {cloud_ready}", "status": cloud_ready},
            {"name": "Device Authentication", "detail": f"Bearer token pair state: {auth_str}", "status": auth_str},
            {"name": "Last Cloud Success", "detail": f"Most recent verified contact: {last_cloud}", "status": last_cloud},
        ]
        full = json.loads(self.app.repository.get_setting("last_full_sync") or "{}") if self.app.repository else {}
        profiles = full.get("profiles", {})
        items.append({"name": "Last Full Sync", "detail": full.get("at") or "Not checked",
                      "status": full.get("result") or "Not checked"})
        items.append({"name": "Profiles", "detail": (
            f"{profiles.get('available', 0)} available, {profiles.get('retired', 0)} retired, "
            f"{profiles.get('authorization_skipped', 0)} unavailable"), "status": "Reconciled" if full else "Not checked"})
        for name, label in (("content", "Content Operations"), ("history", "History Download"),
                            ("heartbeat", "Heartbeat"), ("attempt_uploads", "Attempt Uploads")):
            state = full.get("stages", {}).get(name, "Not checked")
            if isinstance(state, dict):
                state = f"{state.get('uploaded', 0)} uploaded, {state.get('failed', 0)} failed"
            items.append({"name": label, "detail": state, "status": state})
        return items

    # -------------------------------------------------------------------------
    # Slots / Actions
    # -------------------------------------------------------------------------
    @Slot()
    def scanWifi(self):
        if self.app.device and not self.app.device.busy:
            self.app.device.start("wifi_scan")
            self.app.showNotification("Scanning for Wi-Fi networks…", "info")
            self.wifiChanged.emit()

    @Slot(str, str)
    def connectWifi(self, ssid: str, password: str):
        if self.app.device and not self.app.device.busy:
            saved = ssid in set(self.app.device.saved_networks or ())
            self.app.device.start("wifi_connect", ssid=ssid, password=password, saved=saved)
            self.app.showNotification(f"Connecting to {ssid}…", "info")
            self.wifiChanged.emit()

    @Slot(str)
    def forgetWifi(self, ssid: str):
        if self.app.device and not self.app.device.busy:
            self.app.device.start("wifi_forget", ssid=ssid)
            self.app.showNotification(f"Forgot network {ssid}.", "info")
            self.wifiChanged.emit()

    @Slot()
    def startSync(self):
        if self.app.device:
            self.app.device.start("sync")
            self.app.showNotification(self.app.device.message, "info" if self.app.device.busy else "warning")
            self.syncChanged.emit()
            self.accountChanged.emit()

    @Slot()
    def requestPairingCode(self):
        if not self.app.device or self.unlinkPending or (self.hasAccount and self.isPaired):
            return
        if self.app.device.busy:
            if self.app.device.operation == "network" and self.app.screen == "pairing":
                QTimer.singleShot(150, self, lambda: self.requestPairingCode() if self.app.screen == "pairing" else None)
            return
        if self.canRetryAccountSync:
            self.app.device.start("account_sync")
        else:
            self.app.device.start("pair_request", device_id=self.deviceId)
        self.accountChanged.emit()

    @Slot()
    def disconnectAccount(self):
        if self.hasAccount and not self.unlinkPending:
            self._startUnlink("account_disconnect")

    @Slot(str)
    def unlinkProfile(self, profile_id):
        if self.hasAccount and not self.unlinkPending:
            self._startUnlink("profile_unlink", local_profile_id=profile_id)

    @Slot()
    def retryUnlink(self):
        if self.unlinkPending:
            self._startUnlink("unlink_retry")

    def _startUnlink(self, operation, **arguments):
        device = self.app.device
        if device and not device.busy and self.app.screen == "account":
            device.start(operation, **arguments)
            self._unlink_start_error = "" if device.busy else device.message
            self.accountChanged.emit()

    @Slot()
    def checkUpdate(self):
        self.refreshUpdateState()
        device = self.app.device
        if device and not device.busy and not self.updatePendingInstall:
            self._beginUpdateOperation("update_check")
            if device.busy:
                self._recordUpdateCheck()
                self.app.showNotification("Checking for updates...", "info")

    @Slot()
    def downloadUpdate(self):
        self.refreshUpdateState()
        device = self.app.device
        if device and not device.busy and not self.updatePendingInstall and self.updateCompatible:
            self._beginUpdateOperation("update_download", update=self._availableUpdate())

    def _beginUpdateOperation(self, operation, **arguments):
        device = self.app.device
        # A prior status must not override this attempt, but a replacement file can.
        self._ignored_status_revision = self._release_status_revision
        device.start(operation, **arguments)
        self._update_error = "" if device.busy else device.message
        self.refreshUpdateState()

    @Slot()
    def runDiagnostics(self):
        if self.app.device:
            self.app.device.start("diagnostics")
            self.app.showNotification("Running system diagnostics…", "info")
            self.diagnosticsChanged.emit()

    @Slot()
    def exportSupportBundle(self):
        if self.app.device:
            self.app.device.start("export")
            self.app.showNotification("Creating support bundle…", "info")
            self.diagnosticsChanged.emit()
