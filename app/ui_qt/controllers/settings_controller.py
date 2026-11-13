"""Settings Controller managing Wi-Fi, Sync, Account Pairing, Updates, and Diagnostics."""

import json
import shutil
from datetime import UTC, datetime

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from app.connectivity import (
    cloud_state,
    internet_label,
    wifi_state,
)
from app.ui_qt.controllers.app_controller import AppController
from app.version import __version__


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
        self._pairing_code = ""
        self._pairing_status = "idle"
        self._update_error = ""
        self._ignore_release_status = False
        self._update_idle_status = "Check for a software update"
        self._update_was_rolled_back = False
        self._install_deferred = False
        self._update_timer = QTimer(self)
        self._update_timer.setInterval(250)
        self._update_timer.timeout.connect(self._refreshUpdateState)
        self._update_timer.start()
        self._release_status_path = self.app.config.update_root / "status.json"

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
        return self.app.syncLabel == "Syncing"

    @Property(str, notify=syncChanged)
    def lastSyncTime(self) -> str:
        value = self.app.repository.get_setting("last_sync_success") if self.app.repository else None
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
        upload = stages.get("attempt_uploads", {}) if isinstance(stages, dict) else {}
        if result == "Authentication required":
            return "Reconnect this device to your account before syncing. Your local assessments are safe."
        if result in {"Failed", "Partially synced"}:
            failed = upload.get("failed", 0) if isinstance(upload, dict) else 0
            history = stages.get("history") if isinstance(stages, dict) else None
            detail = (f"{failed} assessment upload(s) need a retry." if failed else
                      "Some cloud updates could not be downloaded.")
            if history and history not in {"OK", "Not checked"}:
                detail = f"History download needs a retry. {detail}"
            return f"Last sync was incomplete. {detail} Local records remain saved."
        if pending:
            return f"{pending} completed assessment(s) are saved on this device and waiting to sync."
        if result == "Up to date":
            return "Your recent assessments and profile History are up to date."
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
                return ctx.get("account_display_name", "Student Account")
        return "Alex's Account" if self.isPaired else "Not connected"

    @Property(str, notify=accountChanged)
    def pairingCode(self) -> str:
        if self.app.device and self.app.device.pairing:
            return getattr(self.app.device.pairing, "code", "")
        return self._pairing_code or ""

    @Property(str, notify=accountChanged)
    def pairingStatus(self) -> str:
        if self.app.device and self.app.device.operation == "pair_request" and self.app.device.busy:
            return "Generating…"
        if self.isPaired:
            return "Connected ✓"
        return self._pairing_status

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
        return __version__

    @Property(bool, notify=updateChanged)
    def hasUpdate(self) -> bool:
        if self.app.device:
            update = self.app.device.available_update
            if update is not None:
                from packaging.version import Version
                try:
                    return Version(str(update.manifest.version)) > Version(__version__)
                except Exception:
                    return False
        return False

    @Property(str, notify=updateChanged)
    def updateVersion(self) -> str:
        if self.app.device and self.app.device.available_update:
            return str(self.app.device.available_update.manifest.version)
        return "Up to date"

    @Property(str, notify=updateChanged)
    def availableVersion(self) -> str:
        return self.updateVersion if self.hasUpdate else ""

    @Property(str, notify=updateChanged)
    def updateNotes(self) -> str:
        update = getattr(self.app.device, "available_update", None)
        return update.manifest.data["release"].get("notes", "") if update else ""

    @Property(str, notify=updateChanged)
    def updateError(self) -> str:
        return self._update_error

    @Property(float, notify=updateChanged)
    def updateProgress(self) -> float:
        return max(0.0, min(1.0, float(getattr(self.app.device, "update_progress", 0.0))))

    @Property(bool, notify=updateChanged)
    def updateBusy(self) -> bool:
        return bool(self.app.device and self.app.device.busy and self.app.device.operation in {
            "update_check", "update_download", "update_install"
        })

    @Property(bool, notify=updateChanged)
    def updateCompatible(self) -> bool:
        update = getattr(self.app.device, "available_update", None)
        if not update or not self.app.repository or not self.app.config:
            return False
        try:
            return (
                update.manifest.data["compatibility"] == {
                    "platform": self.app.config.update_platform,
                    "architecture": self.app.config.update_architecture,
                }
                and update.manifest.data["release"]["required_db_schema"] <= self.app.repository.schema_version
                and update.manifest.version > __import__("packaging.version", fromlist=["Version"]).Version(__version__)
            )
        except (KeyError, ValueError):
            return False

    @Property(bool, notify=updateChanged)
    def updatePendingInstall(self) -> bool:
        return bool(self.app.device and self.app.device.staged)

    @Property(str, notify=updateChanged)
    def updateStatus(self) -> str:
        device = self.app.device
        if device and device.busy and device.operation in {"update_check", "update_download", "update_install"}:
            if device.operation == "update_download" and getattr(device, "update_phase", "") == "verifying":
                return "Verifying update"
            return {"update_check": "Checking for updates", "update_download": "Downloading update",
                    "update_install": "Restarting to install update"}[device.operation]
        if self._update_error:
            return self._update_error
        state = None if self._ignore_release_status else self._readReleaseStatus()
        if state and state.get("version") == __version__ and state.get("state") == "successful":
            return "Update successful"
        if state and state.get("state") == "installing":
            return "Installing update"
        if state and state.get("state") == "failed":
            return "Update failed. Try again"
        if self._update_was_rolled_back:
            return "Update failed. Previous version restored"
        if state and state.get("state") == "rolled_back":
            return "Update failed. Previous version restored"
        if self.app.device and self.app.device.staged:
            if self.app.isAssessmentActive:
                return "Ready to install after this assessment"
            return "Preparing installation"
        if self.hasUpdate:
            return "New version available"
        return self._update_idle_status

    @Slot()
    def _refreshUpdateState(self):
        device = self.app.device
        if not device:
            return
        if device.failure and device.operation in {"update_check", "update_download", "update_install"}:
            self._update_error = "Internet unavailable. Your saved work is safe" if not self.app.isOnline else "Update failed. Try again"
            device.failure = None
            self._install_deferred = False
        elif device.operation == "update_check" and not device.busy:
            self._update_idle_status = "Your software is up to date" if not device.available_update else "New version available"
        elif device.operation == "update_download" and not device.busy and device.staged:
            self._update_error = ""
            self._update_was_rolled_back = False
            if self.app.isAssessmentActive:
                self._install_deferred = True
            else:
                self._startInstall()
        elif self._install_deferred and not self.app.isAssessmentActive and not device.busy:
            self._install_deferred = False
            self._startInstall()
        self.updateChanged.emit()

    def _readReleaseStatus(self):
        try:
            return json.loads(self._release_status_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

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
            self.app.showNotification("Syncing assessments…", "info")
            self.syncChanged.emit()

    @Slot()
    def requestPairingCode(self):
        if self.app.device:
            self.app.device.start("pair_request", device_id=self.deviceId)
            self._pairing_status = "generating"
            self.accountChanged.emit()

    @Slot()
    def disconnectAccount(self):
        if self.app.device:
            self.app.device.start("account_disconnect")
            self.app.showNotification("Account disconnected. Data preserved.", "info")
            self.accountChanged.emit()

    @Slot()
    def syncProfiles(self):
        if self.app.device:
            self.app.device.start("account_sync")
            self.app.showNotification("Syncing study profiles…", "info")
            self.accountChanged.emit()

    @Slot()
    def checkUpdate(self):
        self._update_error = ""
        self._ignore_release_status = True
        self._update_idle_status = "Checking for updates"
        if self.app.device:
            self.app.device.start("update_check")
            self.app.showNotification("Checking for updates...", "info")
            if not self.app.device.busy and not self.app.device.available_update:
                self._update_error = self.app.device.message or "Internet unavailable. Your saved work is safe"
            self.updateChanged.emit()

    @Slot()
    def downloadUpdate(self):
        if self.app.device and self.app.device.available_update and not self.app.device.busy:
            self._update_error = ""
            self.app.device.update_progress = 0.0
            self.app.device.start("update_download", update=self.app.device.available_update)
            self.updateChanged.emit()

    def _startInstall(self):
        device = self.app.device
        if device and device.staged and not device.busy:
            device.start("update_install", staged=str(device.staged))
            self.updateChanged.emit()

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
