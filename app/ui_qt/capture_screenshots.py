"""Capture Qt Quick review screenshots at the target Pi display size (800x480)."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QSG_RENDER_LOOP"] = "basic"
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="backslashreplace")

from PySide6.QtCore import QUrl
from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow  # noqa: F401
from PySide6.QtTest import QTest

from app.auth.credentials import CredentialStore
from app.config import AppConfig
from app.core.models import (
    Confidence,
    MarkingScheme,
    Option,
    Profile,
    Question,
    QuestionSet,
)
from app.ui_qt.controllers.app_controller import AppController
from app.ui_qt.controllers.assessment_controller import AssessmentController
from app.ui_qt.controllers.library_controller import LibraryController
from app.ui_qt.controllers.profile_controller import ProfileController
from app.ui_qt.controllers.quick_add_controller import QuickAddController
from app.ui_qt.controllers.settings_controller import SettingsController


def capture_all():
    app = QGuiApplication.instance() or QGuiApplication([])

    # Ensure clean font rendering in offscreen mode
    for font_file in ["segoeui.ttf", "segoeuib.ttf", "segoeuisb.ttf", "arial.ttf", "arialbd.ttf"]:
        font_path = Path("C:/Windows/Fonts") / font_file
        if font_path.exists():
            QFontDatabase.addApplicationFont(str(font_path))
    app.setFont(QFont("Segoe UI", 11))

    # Directories for screenshots
    dirs = [Path("artifacts/pi-ui-verification")]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    capture_data = Path(tempfile.gettempdir()) / "startup-qt-ui-capture"
    capture_data.mkdir(parents=True, exist_ok=True)
    db_path = capture_data / "capture.db"
    db_path.touch(exist_ok=True)

    config = AppConfig(database_path=db_path)
    creds = CredentialStore(db_path.parent / "dev_creds.json")

    app_ctrl = AppController(db_path, config, creds)

    # Setup realistic sample data
    mock_repo = Mock()
    mock_repo.schema_version = 8
    mock_repo.get_or_create_device_id.return_value = "rpi-test-01"
    mock_repo.quick_check.return_value = Mock(ok=True)
    mock_repo.count_attempts_by_sync_status.return_value = 0
    mock_repo.sync_diagnostic_summary.return_value = {"attention_required": False}

    q1 = Question(
        id="q1",
        position=1,
        topic="Cell Biology",
        difficulty=1,
        question_text="Which organelle is primarily responsible for generating cellular ATP through oxidative phosphorylation?",
        options=(
            Option(key="A", text="Mitochondrion (inner folding matrix)"),
            Option(key="B", text="Chloroplast (thylakoid membrane)"),
            Option(key="C", text="Ribosome (polypeptide synthesis)"),
            Option(key="D", text="Endoplasmic reticulum"),
        ),
        correct_key="A",
        explanation="Mitochondria are the primary sites of ATP synthesis in eukaryotic cells via the electron transport chain on the inner mitochondrial membrane.",
    )
    q2 = Question(
        id="q2",
        position=2,
        topic="Cell Biology",
        difficulty=2,
        question_text="What distinguishes eukaryotic plant cells from animal cells?",
        options=(
            Option(key="A", text="Rigid cellulose cell wall and chloroplasts"),
            Option(key="B", text="Presence of a true nucleus"),
            Option(key="C", text="Linear DNA chromosomes"),
            Option(key="D", text="Phospholipid bilayer membrane"),
        ),
        correct_key="A",
        explanation="Plant cells possess a cellulose cell wall, large central vacuole, and plastids such as chloroplasts.",
    )

    qset = QuestionSet(
        id="bio-cell-01",
        version=1,
        title="Cell Structure & Organelles",
        subject="Biology",
        chapter="Cell Biology",
        marking=MarkingScheme(),
        questions=(q1, q2),
    )

    qset2 = QuestionSet(
        id="chem-atom-01",
        version=1,
        title="Atomic Structure & Isotopes",
        subject="Chemistry",
        chapter="Atomic Theory",
        marking=MarkingScheme(),
        questions=(q1,),
    )

    qset3 = QuestionSet(
        id="math-alg-01",
        version=1,
        title="Linear Equations & Inequalities",
        subject="Mathematics",
        chapter="Algebra",
        marking=MarkingScheme(),
        questions=(q1,),
    )

    all_qsets = (qset, qset2, qset3)
    mock_repo.get_question_set.return_value = qset
    mock_repo.list_question_sets.return_value = all_qsets
    mock_repo.visible_question_sets.return_value = all_qsets
    mock_repo.profile_library_catalog.return_value = ()
    mock_repo.institute_work.return_value = ()
    mock_repo.can_start_pack.return_value = True

    # Mock historical attempts
    mock_repo.completed_results.return_value = ()
    mock_repo.save_response.side_effect = lambda resp, **kwargs: resp
    mock_repo.find_in_progress_attempt.return_value = None
    mock_repo.list_attempts.return_value = ()
    mock_repo.get_student_account_context.return_value = {
        "cloud_account_id": "acc-01",
        "account_display_name": "Aksh",
    }

    def fake_get_setting(key):
        if key == "account_profiles":
            return '{"profiles": [{"local_profile_id": "prof-01"}, {"local_profile_id": "prof-02"}]}'
        if key == "network_state":
            return "online"
        return None
    mock_repo.get_setting.side_effect = fake_get_setting
    mock_repo.get_profile_pin.return_value = (None, None)

    prof1 = Profile(
        id="prof-01",
        display_name="Alex",
        cloud_account_id="acc-01",
        cloud_profile_id="c1",
        ownership_state="owned",
        link_state="linked",
    )
    prof2 = Profile(
        id="prof-02",
        display_name="Maya",
        cloud_account_id="acc-01",
        cloud_profile_id="c2",
        ownership_state="owned",
        link_state="linked",
    )
    mock_repo.list_profiles.return_value = (prof1, prof2)

    app_ctrl.startup_session.repository = mock_repo
    app_ctrl.startup_session.complete = True
    app_ctrl._initialize_runtime()

    class MockHist:
        def __init__(self, title, subject, score, maximum, completed_at, sync_status="synced", source="device"):
            self.title = title
            self.subject = subject
            self.score = score
            self.maximum = maximum
            self.completed_at = completed_at
            self.sync_status = Mock(value=sync_status)
            self.source = source
            self.correct = int(score)
            self.wrong = max(0, int(maximum - score))
            self.skipped = 0
            self.answered = self.correct + self.wrong
            self.attempt_id = f"capture-{title.lower().replace(' ', '-')}"
            self.duration_ms = 180000
            self.response_time_ms = 45000
            self.confidence = {
                "sure": {"correct": 1, "wrong": 0},
                "not_sure": {"correct": 1, "wrong": 1},
                "guessing": {"correct": 0, "wrong": 1},
                "unrated": {"correct": 0, "wrong": 0},
            }

    mock_history = (
        MockHist("Cell Structure & Organelles", "Biology", 8.0, 10.0, "01 Nov 2026"),
        MockHist("Atomic Structure & Isotopes", "Chemistry", 9.0, 10.0, "31 Oct 2026"),
        MockHist("Linear Equations & Graphs", "Mathematics", 7.0, 10.0, "30 Oct 2026"),
    )
    type(app_ctrl.ui_controller).history_items = property(lambda self: mock_history)

    engine = QQmlApplicationEngine()
    engine.warnings.connect(lambda warnings: print("QML WARNINGS:", [warning.toString() for warning in warnings]))
    qml_dir = Path("app/ui_qt/qml").resolve()
    engine.addImportPath(str(qml_dir))

    prof_ctrl = ProfileController(app_ctrl)
    lib_ctrl = LibraryController(app_ctrl)
    assess_ctrl = AssessmentController(app_ctrl)
    settings_ctrl = SettingsController(app_ctrl)
    quick_add_ctrl = QuickAddController(app_ctrl)
    settings_ctrl._pairing_code = "K7M2P9"

    ctx = engine.rootContext()
    ctx.setContextProperty("appController", app_ctrl)
    ctx.setContextProperty("profileController", prof_ctrl)
    ctx.setContextProperty("libraryController", lib_ctrl)
    ctx.setContextProperty("assessmentController", assess_ctrl)
    ctx.setContextProperty("settingsController", settings_ctrl)
    ctx.setContextProperty("quickAddController", quick_add_ctrl)

    engine.load(QUrl.fromLocalFile(str(qml_dir / "App.qml")))
    window = engine.rootObjects()[0]
    window.setWidth(800)
    window.setHeight(480)
    window.show()

    def grab_and_save(filename):
        app_ctrl.clearMessage()
        QTest.qWait(60)
        app.processEvents()
        image = window.grabWindow()
        for d in dirs:
            p = d / filename
            image.save(str(p))
        print(f"Captured {filename}: {image.width()}x{image.height()}")

    # 1. Startup screen
    app_ctrl.navigate("startup")
    grab_and_save("01_startup_800x480.png")

    # 2. Profile Picker
    app_ctrl.navigate("profile_picker")
    grab_and_save("02_profile_picker_800x480.png")
    prof_ctrl.selectProfile(0)

    # 3. Home Dashboard (Contextual: ready for new practice)
    app_ctrl.navigate("home")
    grab_and_save("03_home_800x480.png")

    # 4. Subject Selection (Bookshelf)
    app_ctrl.navigate("subjects")
    grab_and_save("04_subjects_800x480.png")

    # 5. Chapters (Biology)
    lib_ctrl.selectSubject("Biology")
    grab_and_save("05_chapters_800x480.png")

    # 6. Question Sets (Packs in Cell Biology)
    lib_ctrl.selectChapter("Cell Biology")
    grab_and_save("06_packs_800x480.png")

    # 7. Test Setup
    lib_ctrl.selectPack("bio-cell-01", 1)
    app_ctrl.navigate("test_setup")
    grab_and_save("07_test_setup_800x480.png")

    # 8. Active Question (Academically focused)
    assess_ctrl.startTest("practice", 10)
    grab_and_save("08_question_800x480.png")

    # 9. Confidence Rating
    app_ctrl.navigate("confidence")
    grab_and_save("09_confidence_800x480.png")

    # 10. Question Navigator
    app_ctrl.navigate("question_nav")
    grab_and_save("10_question_nav_800x480.png")

    # 11. Results (Score & laurel achievement)
    assess_ctrl._result_cache = Mock(
        score=8.0,
        maximum=10.0,
        percentage=80.0,
        confidence_breakdown={Confidence.SURE: 6, Confidence.NOT_SURE: 3, Confidence.GUESSING: 1},
        correct=8,
        wrong=2,
        skipped=0,
    )
    assess_ctrl.resultChanged.emit()
    app_ctrl.navigate("result")
    grab_and_save("11_result_800x480.png")

    # 12. Review Screen
    app_ctrl.navigate("review")
    grab_and_save("12_review_800x480.png")

    # 13. Progress & Analytics
    app_ctrl.navigate("progress")
    grab_and_save("13_progress_analytics_800x480.png")

    # 14. Assessment History
    app_ctrl.navigate("history")
    grab_and_save("14_history_800x480.png")

    # 15. Practice & Downloads (Content)
    app_ctrl.navigate("content")
    grab_and_save("15_content_downloads_800x480.png")

    # 16. Settings Overview
    app_ctrl.navigate("settings")
    grab_and_save("16_settings_800x480.png")

    # 17. Wi-Fi Appliance Screen
    app_ctrl.navigate("wifi")
    grab_and_save("17_wifi_800x480.png")

    # 18. Sync Screen
    app_ctrl.navigate("sync")
    grab_and_save("18_sync_800x480.png")

    # 19. Connected Account & Profiles
    app_ctrl.navigate("account")
    grab_and_save("19_account_800x480.png")

    # 20. Device Info / Specifications
    app_ctrl.navigate("device_info")
    grab_and_save("20_device_info_800x480.png")

    # 21. Diagnostics & Health
    app_ctrl.navigate("diagnostics")
    grab_and_save("21_diagnostics_800x480.png")
    QTest.qWait(500)
    app.processEvents()

    # 22. Software Update
    app_ctrl.navigate("software_update")
    grab_and_save("22_software_update_800x480.png")

    # 23. About Screen
    app_ctrl.navigate("about")
    grab_and_save("23_about_800x480.png")

    # 24. Device Pairing Ticket
    app_ctrl.navigate("pairing")
    grab_and_save("24_pairing_800x480.png")

    # 25. Recovery Mode Screen
    app_ctrl.navigate("recovery")
    grab_and_save("25_recovery_800x480.png")

    # 26. Create Student Profile
    app_ctrl.navigate("create_profile")
    grab_and_save("26_create_profile_800x480.png")

    # 27. Question Detail Passage
    app_ctrl.navigate("question_detail")
    grab_and_save("27_question_detail_800x480.png")

    # QR Quick Add remains part of the normal Pi content workflow.
    app_ctrl.navigate("quick_add")
    grab_and_save("28_quick_add_800x480.png")

    app_ctrl.close()
    print("All 28 Qt review screenshots captured at 800x480 (simulated offscreen rendering).")


if __name__ == "__main__":
    capture_all()
