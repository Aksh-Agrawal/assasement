"""Profile Controller for StudyProfile selection, creation, and PIN unlock."""

import json

from PySide6.QtCore import Property, QObject, Signal, Slot

from app.auth.pin import PinUnlock
from app.ui_qt.controllers.app_controller import AppController


class ProfileController(QObject):
    profilesChanged = Signal()
    pinStateChanged = Signal()

    def __init__(self, app_controller: AppController, parent=None):
        super().__init__(parent)
        self.app = app_controller
        self.app.profile_controller = self
        self.app.activeProfileChanged.connect(self.profilesChanged.emit)
        self._switch_mode = False
        self._pending_profile_id = None
        self._pin_locked = False
        self._pending_profile_index = 0
        self._pin_error = ""

    @Property(bool, notify=profilesChanged)
    def switchMode(self):
        return self._switch_mode

    @Slot()
    def switchProfile(self):
        # Only Home/Account expose switching. Assessment routes cannot switch silently.
        if self.app.screen not in {"home", "account"}:
            return
        self._switch_mode = True
        self._pin_locked = False
        self.profilesChanged.emit()
        self.app.navigate("profile_picker")

    @Slot()
    def cancelSwitch(self):
        self.cancelPin()
        self._switch_mode = False
        self.profilesChanged.emit()
        self.app.goHome()

    @Property(list, notify=profilesChanged)
    def profiles(self) -> list:
        if not self.app.ui_controller:
            return []
        cached = json.loads(self.app.repository.get_setting("account_profiles") or "{}")
        metadata = {p["local_profile_id"]: p for p in cached.get("profiles", [])}
        res = []
        for i, p in enumerate(self.app.ui_controller.profiles):
            has_pin = False
            if self.app.repository:
                has_pin = PinUnlock(self.app.repository).protected(p.id)
            res.append({
                "index": i,
                "id": p.id,
                "name": p.display_name,
                "grade": metadata.get(p.id, {}).get("exam_context", ""),
                "isActive": (self.app.ui_controller.selected_profile and self.app.ui_controller.selected_profile.id == p.id),
                "hasPin": has_pin,
                "ownershipState": p.ownership_state,
            })
        return res

    @Property(int, notify=profilesChanged)
    def profileCount(self) -> int:
        return len(self.profiles)

    @Property(bool, notify=profilesChanged)
    def canAddProfile(self) -> bool:
        return self.profileCount < 3

    @Property(bool, notify=pinStateChanged)
    def pinLocked(self) -> bool:
        return self._pin_locked

    @Property(str, notify=pinStateChanged)
    def pinProfileName(self) -> str:
        return next((p["name"] for p in self.profiles if p["id"] == self._pending_profile_id), "Student")

    @Property(str, notify=pinStateChanged)
    def pinError(self) -> str:
        return self._pin_error

    @Slot(int)
    def selectProfile(self, index: int):
        if not self.app.ui_controller:
            return
        if self.app.isAssessmentActive:
            return
        profs = self.profiles
        if not (0 <= index < len(profs)):
            return
        self.selectProfileId(profs[index]["id"])

    @Slot(str)
    def selectProfileId(self, profile_id):
        if not self.app.ui_controller or self.app.isAssessmentActive:
            return
        self.app.ui_controller.refresh_catalog()
        profile_data = next((p for p in self.profiles if p["id"] == profile_id), None)
        if not profile_data:
            return
        index = profile_data["index"]
        self._pending_profile_index = index
        self._pending_profile_id = profile_id

        # Check PIN
        if profile_data["hasPin"]:
            self._pin_locked = True
            self._pin_error = ""
            self.pinStateChanged.emit()
        else:
            self._activate_profile(index)

    def _activate_profile(self, index: int):
        ui = self.app.ui_controller
        ui.refresh_catalog()
        profile = next((p for p in ui.profiles if p.id == self._pending_profile_id), None)
        if profile is None or (profile.ownership_state == "owned" and profile.link_state != "linked"):
            self.cancelPin()
            self.profilesChanged.emit()
            return
        ui.application.pause()
        from app.assessment import AssessmentApplication
        ui.application = AssessmentApplication(self.app.repository)
        ui.profile_index = ui.profiles.index(profile)
        ui.subject_index = ui.chapter_index = ui.set_index = ui.navigator_index = 0
        ui.institute_assignment = None
        ui.result = None
        ui.review_items = ui.all_review_items = ()
        ui.review_index = 0
        ui.refresh_catalog()
        self.app.repository.set_setting("last_active_profile_id", profile.id)
        self.app._active_profile_id = profile.id
        self.app._screen_history.clear()
        library = getattr(self.app, "library_controller", None)
        if library:
            library._selected_subject = library._selected_chapter = library._selected_pack_id = ""
            library._selected_pack_version = 0
            library.refreshLibrary()
        assessment = getattr(self.app, "assessment_controller", None)
        if assessment:
            assessment.resetProfileState()
        self._switch_mode = False
        self._pin_locked = False
        self.pinStateChanged.emit()
        self.profilesChanged.emit()
        self.app.activeProfileChanged.emit()
        self.app.navigate("home")

    @Slot(str)
    def submitPin(self, pin: str):
        if not self.app.repository:
            return
        profs = self.profiles
        if not (0 <= self._pending_profile_index < len(profs)):
            return
        self.app.ui_controller.refresh_catalog()
        profile_id = self._pending_profile_id
        if profile_id not in {p.id for p in self.app.ui_controller.profiles}:
            self.cancelPin()
            return
        pin_service = PinUnlock(self.app.repository)
        unlocked, message = pin_service.unlock(profile_id, pin)
        if unlocked:
            self._pin_error = ""
            self._activate_profile(self._pending_profile_index)
        else:
            self._pin_error = message
            self.pinStateChanged.emit()

    @Slot()
    def cancelPin(self):
        self._pin_locked = False
        self._pin_error = ""
        self.pinStateChanged.emit()

    @Slot(str, str)
    def createProfile(self, display_name: str, grade: str = "Primary 6"):
        name = display_name.strip()
        if not name:
            self.app.showNotification("Please enter a profile name.", "warning")
            return
        if self.profileCount >= 3:
            self.app.showNotification("Maximum 3 Study Profiles allowed.", "warning")
            return

        if self.app.device:
            self.app.device.start("account_create", create={"name": name, "exam_context": grade})
            self.app.showNotification("Creating Study Profile…", "info")
