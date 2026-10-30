"""Profile Controller for StudyProfile selection, creation, and PIN unlock."""

from uuid import uuid4

from PySide6.QtCore import Property, QObject, Signal, Slot

from app.auth.pin import PinUnlock
from app.core.models import Profile
from app.ui_qt.controllers.app_controller import AppController


class ProfileController(QObject):
    profilesChanged = Signal()
    pinStateChanged = Signal()

    def __init__(self, app_controller: AppController, parent=None):
        super().__init__(parent)
        self.app = app_controller
        self._pin_locked = False
        self._pending_profile_index = 0
        self._pin_error = ""

    @Property(list, notify=profilesChanged)
    def profiles(self) -> list:
        if not self.app.ui_controller:
            return []
        res = []
        for i, p in enumerate(self.app.ui_controller.profiles):
            has_pin = False
            if self.app.repository:
                has_pin = PinUnlock(self.app.repository).protected(p.id)
            res.append({
                "index": i,
                "id": p.id,
                "name": p.display_name,
                "grade": getattr(p, "grade", "Primary 6") or "Primary 6",
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
        profs = self.profiles
        if 0 <= self._pending_profile_index < len(profs):
            return profs[self._pending_profile_index]["name"]
        return "Student"

    @Property(str, notify=pinStateChanged)
    def pinError(self) -> str:
        return self._pin_error

    @Slot(int)
    def selectProfile(self, index: int):
        if not self.app.ui_controller:
            return
        profs = self.profiles
        if not (0 <= index < len(profs)):
            return

        self._pending_profile_index = index
        profile_data = profs[index]

        # Check PIN
        if profile_data["hasPin"]:
            self._pin_locked = True
            self._pin_error = ""
            self.pinStateChanged.emit()
        else:
            self._activate_profile(index)

    def _activate_profile(self, index: int):
        self.app.ui_controller.profile_index = index
        self.app.ui_controller.refresh_catalog()
        if getattr(self.app, "library_controller", None):
            self.app.library_controller.refreshLibrary()
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
        profile_id = profs[self._pending_profile_index]["id"]
        pin_service = PinUnlock(self.app.repository)
        if pin_service.verify(profile_id, pin):
            self._pin_error = ""
            self._activate_profile(self._pending_profile_index)
        else:
            self._pin_error = "Incorrect PIN. Try again."
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

        try:
            profile = Profile(id=str(uuid4()), display_name=name)
            if self.app.repository:
                self.app.repository.create_profile(profile)
            if self.app.ui_controller:
                self.app.ui_controller.refresh_catalog()
                self.app.ui_controller.profile_index = len(self.app.ui_controller.profiles) - 1

            self.profilesChanged.emit()
            self.app.activeProfileChanged.emit()
            self.app.showNotification(f"Created profile for {name}!", "success")
            self.app.navigate("home")
        except Exception as err:
            self.app.showNotification(f"Could not create profile: {err}", "error")
