"""Library Controller for subjects, chapters, and assessment packs."""

from PySide6.QtCore import Property, QObject, Signal, Slot

from app.api.transport import FailureState
from app.connectivity import internet_label
from app.content.client import QUESTION_BANK_PAGE_SIZE
from app.ui_qt.controllers.app_controller import AppController


class LibraryController(QObject):
    catalogChanged = Signal()
    selectionChanged = Signal()
    bankCatalogChanged = Signal()

    def __init__(self, app_controller: AppController, parent=None):
        super().__init__(parent)
        self.app = app_controller
        self.app.library_controller = self
        self._selected_subject = ""
        self._selected_chapter = None
        self._selected_pack_id = ""
        self._selected_pack_version = 0
        self._installed_only = False
        self._browsing = False
        self._bank_scope = None
        self._bank_connectivity = ""
        self._bank_filters = ("", "", "")
        self._bank_offset = 0
        self._bank_next = None
        self._bank_packs = ()
        self._bank_state = "idle"
        self._bank_request = None
        self._bank_download = None
        self._bank_download_phase = ""
        self._failed_bank_download = None
        self.app.deviceOperationFinished.connect(self._device_finished)
        self.app.screenChanged.connect(self._screen_changed)

    def _local_sets(self):
        ui = self.app.ui_controller
        return tuple(pack for pack in ui.question_sets if pack.questions) if ui and ui.selected_profile else ()

    @staticmethod
    def _latest_versions(packs, identify):
        latest = {}
        for pack in packs:
            key = identify(pack)
            if key not in latest or pack.version > latest[key].version:
                latest[key] = pack
        return tuple(latest.values())

    def _installed_packs(self):
        return self._latest_versions(self._local_sets(), lambda pack: pack.id)

    def _delivered_packs(self):
        ui = self.app.ui_controller
        if not ui or not ui.selected_profile:
            return ()
        return self._latest_versions(ui.remote_packs, lambda pack: pack.set_id)

    @staticmethod
    def _subject_rows(packs):
        subjects = {}
        for pack in packs:
            chapters = subjects.setdefault(pack.subject, set())
            if pack.chapter:
                chapters.add(pack.chapter)
        return [{"name": name, "chapters": " • ".join(sorted(chapters, key=str.casefold))}
                for name, chapters in sorted(subjects.items(), key=lambda entry: entry[0].casefold())]

    @Property(list, notify=catalogChanged)
    def homeSubjects(self) -> list:
        return self._subject_rows(self._installed_packs())

    @Property(list, notify=catalogChanged)
    def subjectCards(self) -> list:
        return self._subject_rows((*self._installed_packs(), *self._delivered_packs()))

    @Property(list, notify=catalogChanged)
    def subjects(self) -> list:
        return [subject["name"] for subject in self.subjectCards]

    @Property(str, notify=selectionChanged)
    def selectedSubject(self) -> str:
        return self._selected_subject

    @Property(list, notify=selectionChanged)
    def chapters(self) -> list:
        remote = () if self._installed_only else self._delivered_packs()
        return sorted({p.chapter for p in (*self._installed_packs(), *remote)
                       if p.subject == self._selected_subject}, key=str.casefold)

    @Property(str, notify=selectionChanged)
    def selectedChapter(self) -> str:
        return self._selected_chapter or ""

    @staticmethod
    def _local_row(pack):
        topics = {question.topic for question in pack.questions}
        topic = next(iter(topics)) if len(topics) == 1 else ""
        if topic == pack.chapter:
            topic = ""
        return {"id": pack.id, "version": pack.version, "title": pack.title,
                "subject": pack.subject, "chapter": pack.chapter, "topic": topic,
                "questionCount": len(pack.questions),
                "isInstalled": True, "isDownloading": False, "status": "Ready offline"}

    @Property(list, notify=catalogChanged)
    def installedPacks(self) -> list:
        return [self._local_row(pack) for pack in self._installed_packs()]

    @Property(list, notify=selectionChanged)
    def packs(self) -> list:
        if self._selected_chapter not in self.chapters:
            return []
        context = self._selected_subject, self._selected_chapter
        results = [self._local_row(pack) for pack in self._installed_packs()
                   if (pack.subject, pack.chapter) == context]
        if self._installed_only:
            return results
        installed = {(p["id"], p["version"]) for p in results}
        for pack in self._delivered_packs():
            if (pack.subject, pack.chapter) == context and (pack.set_id, pack.version) not in installed:
                state = self.app.device.download_state.get((pack.set_id, pack.version), "")
                results.append({
                    "id": pack.set_id, "version": pack.version, "title": pack.title,
                    "subject": pack.subject, "chapter": pack.chapter, "questionCount": pack.question_count,
                    "isInstalled": False, "isDownloading": state in {"QUEUED", "DOWNLOADING"},
                    "status": "Available to download",
                })
        return results

    @Property(dict, notify=selectionChanged)
    def selectedPack(self) -> dict:
        pack = self.selected_practice_set()
        return self._local_row(pack) if pack else {}

    def selected_practice_set(self):
        return next((pack for pack in self._local_sets()
                     if (pack.id, pack.version) == (self._selected_pack_id, self._selected_pack_version)), None)

    @Property(list, notify=selectionChanged)
    def practiceTopics(self) -> list:
        question_set = self.selected_practice_set()
        return ["All topics", *sorted({q.topic for q in question_set.questions})] if question_set else ["All topics"]

    @Property(int, notify=selectionChanged)
    def practiceQuestionTotal(self) -> int:
        question_set = self.selected_practice_set()
        return len(question_set.questions) if question_set else 0

    @Slot(str, str, result=int)
    def practiceQuestionCount(self, topic_label: str, difficulty_label: str) -> int:
        question_set = self.selected_practice_set()
        if not question_set:
            return 0
        topic = "" if topic_label == "All topics" else topic_label
        difficulty = {"Foundation": "foundation", "Standard": "standard", "Challenge": "challenge"}.get(difficulty_label, "")
        bands = {1: "foundation", 2: "foundation", 3: "standard", 4: "challenge", 5: "challenge"}
        return sum(1 for q in question_set.questions
                   if (not topic or q.topic == topic)
                   and (not difficulty or bands[q.difficulty] == difficulty))

    @Slot(str, str, result=list)
    def practiceCountPresets(self, topic_label: str, difficulty_label: str) -> list:
        eligible = self.practiceQuestionCount(topic_label, difficulty_label)
        if eligible <= 0:
            return []
        presets = ["All questions"]
        presets.extend(f"{count} questions" for count in (5, 10, 20) if count <= eligible)
        presets.append("Custom")
        return presets

    @Property(bool, notify=bankCatalogChanged)
    def browsingBanks(self):
        return self._browsing

    @Property(str, notify=bankCatalogChanged)
    def bankState(self):
        return self._bank_state

    @Property(list, notify=bankCatalogChanged)
    def bankFilters(self):
        return list(self._bank_filters)

    @Property(bool, notify=bankCatalogChanged)
    def hasNextBankPage(self):
        return self._bank_state == "ready" and self._bank_next is not None

    @Property(bool, notify=bankCatalogChanged)
    def hasPreviousBankPage(self):
        return self._bank_state == "ready" and self._bank_offset > 0

    @Property(str, notify=catalogChanged)
    def libraryConnection(self):
        if not self.app.repository:
            return "checking"
        internet = internet_label(self.app.repository)
        cloud = self.app.networkLabel
        if cloud == "Authentication required":
            return "auth"
        if self.app.isOnline:
            return "online"
        if internet == "Unavailable" or (cloud == "Offline" and internet != "Available"):
            return "offline"
        if internet == "Available" or cloud == "Server unavailable":
            return "unreachable"
        return "checking"

    @Property(list, notify=bankCatalogChanged)
    def questionBanks(self):
        installed = {(p.id, p.version) for p in self._local_sets()}
        rows = []
        for pack in self._bank_packs:
            identity = self._bank_scope, pack.set_id, pack.version
            ready = (pack.set_id, pack.version) in installed
            active = identity == self._bank_download
            failed = identity == self._failed_bank_download
            status = ("Ready offline" if ready else self._bank_download_phase if active
                      else "Download failed" if failed else "Available")
            rows.append({"id": pack.set_id, "version": pack.version, "title": pack.title,
                         "subject": pack.subject, "chapter": pack.chapter, "questionCount": pack.question_count,
                         "isInstalled": ready, "isDownloading": active and not ready,
                         "status": status, "retry": failed})
        return rows

    def _linked_scope(self):
        ui = self.app.ui_controller
        profile = ui.selected_profile if ui else None
        if not profile or ui.authorized_profile != profile.id or profile.link_state != "linked":
            return None
        context = self.app.repository.get_profile_link_context(profile.id)
        return (profile.id, context["link_id"]) if context else None

    @Slot(bool)
    def setBrowsingBanks(self, active):
        if active != self._browsing:
            self._browsing = active
            if active:
                self._load_bank_page(0)
            else:
                self.bankCatalogChanged.emit()

    @Slot()
    def openQuestionBanks(self):
        self.setBrowsingBanks(True)
        self.app.navigate("content")

    @Slot(str, str, str)
    def filterBanks(self, search, subject, chapter):
        self._bank_filters = tuple(value.strip()[:200] for value in (search, subject, chapter))
        self._load_bank_page(0)

    @Slot()
    def refreshBanks(self):
        self._load_bank_page(0)

    @Slot()
    def nextBankPage(self):
        if self.hasNextBankPage:
            self._load_bank_page(self._bank_next)

    @Slot()
    def previousBankPage(self):
        if self.hasPreviousBankPage:
            self._load_bank_page(max(0, self._bank_offset - QUESTION_BANK_PAGE_SIZE))

    def _screen_changed(self):
        if self._browsing and self.app.screen == "content":
            self._load_bank_page(0)

    def _load_bank_page(self, offset):
        self._bank_offset = offset
        self._bank_next = None
        self._bank_packs = ()
        self._bank_state = "loading"
        self.bankCatalogChanged.emit()

    def tick(self):
        device = self.app.device
        if self._bank_download and device.bank_download_phase in {"Downloading", "Verifying"}:
            if device.bank_download_phase != self._bank_download_phase:
                self._bank_download_phase = device.bank_download_phase
                self.bankCatalogChanged.emit()
        if not self._browsing or self.app.screen != "content":
            return
        scope, connectivity = self._linked_scope(), self.libraryConnection
        if scope != self._bank_scope or connectivity != self._bank_connectivity:
            self._bank_scope, self._bank_connectivity = scope, connectivity
            self._load_bank_page(0)
        state = ""
        if connectivity == "offline":
            state = "offline"
        elif not scope or connectivity == "auth" or not self.app.credentials.load_safe():
            state = "auth"
        elif not self.app.config.api_base_url:
            state = "unreachable"
        if state:
            if state != self._bank_state:
                self._bank_packs = ()
                self._bank_state = state
                self.bankCatalogChanged.emit()
            return
        if self._bank_state == "loading" and not device.busy:
            search, subject, chapter = self._bank_filters
            query = {"search": search, "subject": subject, "chapter": chapter, "offset": self._bank_offset}
            device.start("browse_banks", scope=scope, query=query)
            self._bank_request = scope, self._bank_filters, self._bank_offset

    @Slot(str, int)
    def downloadBank(self, set_id, version):
        scope = self._linked_scope()
        if not scope or scope != self._bank_scope or self._bank_state != "ready":
            return
        if any((p.id, p.version) == (set_id, version) for p in self._local_sets()):
            self.selectPack(set_id, version)
            return
        pack = next((p for p in self._bank_packs if (p.set_id, p.version) == (set_id, version)), None)
        if not pack:
            return
        device = self.app.device
        if device.busy:
            self.app.showNotification("Wait for the current device action, then try again.", "info")
            return
        device.start("download_bank", scope=scope, pack=pack)
        if device.busy:
            self._bank_download = scope, set_id, version
            self._bank_download_phase = "Downloading"
            self._failed_bank_download = None
            self.bankCatalogChanged.emit()
        else:
            self.app.showNotification(device.message, "warning")

    def _device_finished(self, operation):
        device = self.app.device
        if operation == "browse_banks":
            request, self._bank_request = self._bank_request, None
            if (self._bank_state != "loading" or self._linked_scope() != self._bank_scope
                    or request != (self._bank_scope, self._bank_filters, self._bank_offset)):
                return
            if device.bank_page is not None:
                self._bank_packs, self._bank_next = device.bank_page
                self._bank_state = "ready"
            else:
                self._bank_state = ("auth" if device.failure == FailureState.AUTH_REQUIRED
                                    else "offline" if self.libraryConnection == "offline" else "unreachable")
            self.bankCatalogChanged.emit()
        elif operation == "download_bank":
            download = self._bank_download
            self._bank_download = None
            if device.bank_download_phase == "SUPERSEDED" and download and download[0] == self._linked_scope():
                self._load_bank_page(0)
                return
            if device.bank_download_phase not in {"INSTALLED", "ALREADY_PRESENT"}:
                self._failed_bank_download = download
            self.bankCatalogChanged.emit()
        elif operation == "network" and self.app.isOnline and self._bank_state in {"offline", "unreachable"}:
            self._load_bank_page(0)

    @Property(bool, notify=catalogChanged)
    def canResume(self) -> bool:
        if self.app.ui_controller:
            return self.app.ui_controller.can_resume
        return False

    @Property(str, notify=catalogChanged)
    def resumeTitle(self) -> str:
        if self.app.ui_controller and self.app.ui_controller.resume_summary:
            return self.app.ui_controller.resume_summary[0]
        return ""

    @Property(int, notify=catalogChanged)
    def resumeAnswered(self) -> int:
        if self.app.ui_controller and self.app.ui_controller.resume_summary:
            return self.app.ui_controller.resume_summary[1]
        return 0

    @Property(int, notify=catalogChanged)
    def resumeTotal(self) -> int:
        if self.app.ui_controller and self.app.ui_controller.resume_summary:
            return self.app.ui_controller.resume_summary[2]
        return 0

    @Slot(str)
    def selectSubject(self, name: str):
        self._open_subject(name, installed_only=False)

    @Slot(str)
    def selectInstalledSubject(self, name: str):
        self._open_subject(name, installed_only=True)

    def _open_subject(self, name, *, installed_only):
        self._installed_only = installed_only
        self._selected_subject = name
        self._selected_chapter = None
        self._clear_pack()
        self.selectionChanged.emit()
        self.app.navigate("chapters")

    @Slot(str)
    def selectChapter(self, name: str):
        self._selected_chapter = name
        self._clear_pack()
        self.selectionChanged.emit()
        self.app.navigate("packs")

    @Slot(str, int)
    def selectPack(self, pack_id: str, version: int):
        pack = next((p for p in self._local_sets() if (p.id, p.version) == (pack_id, version)), None)
        if pack is None:
            self._clear_pack()
            self.selectionChanged.emit()
            self.app.showNotification("This practice pack is no longer available.", "warning")
            return
        self._selected_subject, self._selected_chapter = pack.subject, pack.chapter
        self._selected_pack_id, self._selected_pack_version = pack_id, version
        self.selectionChanged.emit()
        self.app.navigate("test_setup")

    def _clear_pack(self):
        self._selected_pack_id, self._selected_pack_version = "", 0

    def reset_profile(self):
        self._selected_subject, self._selected_chapter = "", None
        self._installed_only = False
        self._clear_pack()
        self._browsing = False
        self._bank_scope = self._bank_request = self._failed_bank_download = None
        self._bank_filters = ("", "", "")
        self._load_bank_page(0)

    @Slot(str, int)
    def downloadPack(self, pack_id: str, version: int):
        if not self.app.device or not self.app.ui_controller:
            return
        # Find matching remote pack
        for r in self.app.ui_controller.remote_packs:
            if r.set_id == pack_id and r.version == version:
                profile = self.app.ui_controller.selected_profile
                self.app.device.start("download", pack=r, local_profile_id=profile.id if profile else None)
                self.app.showNotification(self.app.device.message, "info" if self.app.device.busy else "warning")
                self.selectionChanged.emit()
                return
        self.app.showNotification("Pack not found in catalog.", "warning")

    @Slot()
    def refreshLibrary(self):
        if self.app.ui_controller:
            self.app.ui_controller.repository.reconcile_content_state()
            self.app.ui_controller.refresh_catalog()
            cleared = self.app.ui_controller.application.reconcile_session()
            assessment = getattr(self.app, "assessment_controller", None)
            if cleared and assessment:
                assessment._active = False
                assessment._countdown_timer.stop()
                assessment._timer_enabled = False
                assessment._timer_seconds = 0
                assessment.timerChanged.emit()
                assessment.questionChanged.emit()
                assessment.navigatorChanged.emit()
                self.app.navigate("home")
        if self._selected_pack_id and self.selected_practice_set() is None:
            self._clear_pack()
        self.catalogChanged.emit()
        self.selectionChanged.emit()
        if self._browsing:
            self.bankCatalogChanged.emit()
