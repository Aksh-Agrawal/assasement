"""Settings Controller managing Wi-Fi, Sync, Account Pairing, Updates, and Diagnostics."""

import shutil

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

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

    # -------------------------------------------------------------------------
    # Wi-Fi & Network Properties
    # -------------------------------------------------------------------------
    @Property(bool, notify=wifiChanged)
    def isWifiConnected(self) -> bool:
        if self.app.device:
            return bool(self.app.device.wifi_connected)
        return False

    @Property(str, notify=wifiChanged)
    def connectedSsid(self) -> str:
        if self.app.device and self.app.device.saved_networks:
            return self.app.device.saved_networks[0]
        return "StudyBuddy-Home" if self.isWifiConnected else "Not connected"

    @Property(str, notify=wifiChanged)
    def internetStatus(self) -> str:
        if self.app.device:
            return self.app.device.internet_status
        return "Available" if self.app.isOnline else "Unavailable"

    @Property(str, notify=wifiChanged)
    def cloudStatus(self) -> str:
        return self.app.networkLabel

    @Property(list, notify=wifiChanged)
    def availableNetworks(self) -> list:
        if not self.app.device or not self.app.device.networks:
            # Fallback realistic sample networks for discovery/dev
            return [
                {"ssid": "StudyBuddy-Home", "connected": True, "saved": True, "signal": 90, "encrypted": True},
                {"ssid": "HomeWiFi", "connected": False, "saved": False, "signal": 75, "encrypted": True},
                {"ssid": "SchoolWiFi", "connected": False, "saved": False, "signal": 60, "encrypted": True},
                {"ssid": "Library-Guest", "connected": False, "saved": False, "signal": 40, "encrypted": False},
            ]
        saved = set(self.app.device.saved_networks)
        res = []
        for n in self.app.device.networks:
            ssid = getattr(n, "ssid", str(n))
            res.append({
                "ssid": ssid,
                "connected": (ssid == self.connectedSsid),
                "saved": (ssid in saved),
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
        from datetime import UTC, datetime
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
        from datetime import UTC, datetime
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
            return getattr(self.app.device.pairing, "code", "A7K392")
        return self._pairing_code or "A7K392"

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
                "title": p.title,
                "subject": p.subject,
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
            return self.app.device.available_update is not None
        return False

    @Property(str, notify=updateChanged)
    def updateVersion(self) -> str:
        if self.app.device and self.app.device.available_update:
            return getattr(self.app.device.available_update, "target_version", "1.2.1")
        return "Up to date"

    @Property(str, notify=updateChanged)
    def updateStatus(self) -> str:
        if self.app.device and self.app.device.staged:
            return "Update verified and staged"
        if self.hasUpdate:
            return "New version available"
        return "Your software is up to date"

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

    # -------------------------------------------------------------------------
    # Slots / Actions
    # -------------------------------------------------------------------------
    @Slot()
    def scanWifi(self):
        if self.app.device:
            self.app.device.start("wifi_scan")
            self.app.showNotification("Scanning for Wi-Fi networks…", "info")
            self.wifiChanged.emit()

    @Slot(str, str)
    def connectWifi(self, ssid: str, password: str):
        if self.app.device:
            self.app.device.start("wifi_connect", ssid=ssid, password=password)
            self.app.showNotification(f"Connecting to {ssid}…", "info")
            self.wifiChanged.emit()

    @Slot(str)
    def forgetWifi(self, ssid: str):
        if self.app.device:
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
        if self.app.device:
            self.app.device.start("update_check")
            self.app.showNotification("Checking for updates…", "info")
            self.updateChanged.emit()

    @Slot()
    def downloadUpdate(self):
        if self.app.device:
            self.app.device.start("update_download", update=self.app.device.available_update)
            self.app.showNotification("Downloading update…", "info")
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
