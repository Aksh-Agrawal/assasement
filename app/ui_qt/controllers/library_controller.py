"""Library Controller for subjects, chapters, and assessment packs."""

from PySide6.QtCore import Property, QObject, Signal, Slot

from app.ui_qt.controllers.app_controller import AppController


class LibraryController(QObject):
    catalogChanged = Signal()
    selectionChanged = Signal()

    def __init__(self, app_controller: AppController, parent=None):
        super().__init__(parent)
        self.app = app_controller
        self.app.library_controller = self
        self._selected_subject = "Mathematics"
        self._selected_chapter = ""
        self._selected_pack_id = ""
        self._selected_pack_version = 1

    @Property(list, notify=catalogChanged)
    def subjects(self) -> list:
        if not self.app.ui_controller:
            return ["Mathematics", "Science", "English", "General Knowledge"]
        subs = list(self.app.ui_controller.subjects)
        if not subs:
            return ["Mathematics", "Science", "English", "General Knowledge"]
        return subs

    @Property(str, notify=selectionChanged)
    def selectedSubject(self) -> str:
        subs = self.subjects
        if self._selected_subject not in subs and subs:
            return subs[0]
        return self._selected_subject

    @Property(list, notify=selectionChanged)
    def chapters(self) -> list:
        if not self.app.ui_controller:
            return []
        subj = self.selectedSubject
        all_sets = (*self.app.ui_controller.question_sets, *self.app.ui_controller.remote_packs)
        chaps = sorted({s.chapter for s in all_sets if s.subject == subj and getattr(s, "chapter", None)})
        return chaps if chaps else ["General Practice"]

    @Property(str, notify=selectionChanged)
    def selectedChapter(self) -> str:
        chaps = self.chapters
        if self._selected_chapter not in chaps and chaps:
            return chaps[0]
        return self._selected_chapter

    @Property(list, notify=selectionChanged)
    def packs(self) -> list:
        if not self.app.ui_controller:
            return []
        subj = self.selectedSubject
        chap = self.selectedChapter
        results = []

        # Local installed sets
        for item in self.app.ui_controller.question_sets:
            if item.subject == subj and (not chap or item.chapter == chap):
                results.append({
                    "id": item.id,
                    "version": item.version,
                    "title": item.title,
                    "subject": item.subject,
                    "chapter": item.chapter,
                    "questionCount": len(item.questions),
                    "badge": "Official",
                    "isInstalled": True,
                    "isDownloading": False,
                    "isRecommended": True,
                })

        # Remote / downloadable packs
        for r in self.app.ui_controller.remote_packs:
            if r.subject == subj and (not chap or r.chapter == chap):
                # Check if already installed
                already = any(p["id"] == r.set_id and p["version"] == r.version for p in results)
                if not already:
                    dl_state = self.app.device.download_state.get((r.set_id, r.version), "")
                    results.append({
                        "id": r.set_id,
                        "version": r.version,
                        "title": r.title,
                        "subject": r.subject,
                        "chapter": r.chapter,
                        "questionCount": getattr(r, "question_count", 10),
                        "badge": "Sample" if getattr(r, "sample", False) else "Catalog",
                        "isInstalled": False,
                        "isDownloading": dl_state in {"QUEUED", "DOWNLOADING"},
                        "isRecommended": False,
                    })
        return results

    @Property(dict, notify=selectionChanged)
    def selectedPack(self) -> dict:
        pk_list = self.packs
        for p in pk_list:
            if p["id"] == self._selected_pack_id and p["version"] == self._selected_pack_version:
                return p
        return pk_list[0] if pk_list else {}

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
        self._selected_subject = name
        self._selected_chapter = ""
        self.selectionChanged.emit()
        self.app.navigate("chapters")

    @Slot(str)
    def selectChapter(self, name: str):
        self._selected_chapter = name
        self.selectionChanged.emit()
        self.app.navigate("packs")

    @Slot(str, int)
    def selectPack(self, pack_id: str, version: int):
        self._selected_pack_id = pack_id
        self._selected_pack_version = version

        if self.app.ui_controller:
            for qs in self.app.ui_controller.question_sets:
                if qs.id == pack_id and qs.version == version:
                    if qs.subject in self.app.ui_controller.subjects:
                        self.app.ui_controller.subject_index = self.app.ui_controller.subjects.index(qs.subject)
                        self._selected_subject = qs.subject
                    if getattr(qs, "chapter", None):
                        self._selected_chapter = qs.chapter
                    matching_sets = self.app.ui_controller.subject_question_sets
                    for s_idx, s_item in enumerate(matching_sets):
                        if s_item.id == pack_id and s_item.version == version:
                            self.app.ui_controller.set_index = s_idx
                            break
                    break

        self.selectionChanged.emit()
        self.app.navigate("test_setup")

    @Slot(str, int)
    def downloadPack(self, pack_id: str, version: int):
        if not self.app.device:
            return
        # Find matching remote pack
        for r in self.app.ui_controller.remote_packs:
            if r.set_id == pack_id and r.version == version:
                self.app.device.start("download", pack=r)
                self.app.showNotification(f"Downloading {r.title}…", "info")
                self.selectionChanged.emit()
                return
        self.app.showNotification("Pack not found in catalog.", "warning")

    @Slot()
    def refreshLibrary(self):
        if self.app.ui_controller:
            self.app.ui_controller.refresh_catalog()
        self.catalogChanged.emit()
        self.selectionChanged.emit()
