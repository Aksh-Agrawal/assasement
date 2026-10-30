"""Capture development screenshots of major Qt Quick screens at exactly 800x480."""

import os
from pathlib import Path
from unittest.mock import Mock

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QSG_RENDER_LOOP"] = "basic"

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow  # noqa: F401

from app.auth.credentials import CredentialStore
from app.config import AppConfig
from app.core.models import Confidence, MarkingScheme, Option, Profile, Question, QuestionSet
from app.ui_qt.controllers.app_controller import AppController
from app.ui_qt.controllers.assessment_controller import AssessmentController
from app.ui_qt.controllers.library_controller import LibraryController
from app.ui_qt.controllers.profile_controller import ProfileController
from app.ui_qt.controllers.settings_controller import SettingsController


def capture_all():
    app = QGuiApplication.instance() or QGuiApplication([])

    output_dir = Path("var/screenshots/qt_800x480")
    output_dir.mkdir(parents=True, exist_ok=True)

    db_path = Path("var/dev_test.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.touch()

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

    qset = QuestionSet(
        id="bio-pack-01",
        version=1,
        title="Fractions & Decimals Practice",
        subject="Biology",
        chapter="Fractions",
        marking=MarkingScheme(),
        questions=(
            Question(
                id="q1",
                position=1,
                topic="Fractions",
                difficulty=1,
                question_text="What fraction of this shape is shaded?",
                options=(
                    Option(key="A", text="1/4 of total area"),
                    Option(key="B", text="1/2 of total area"),
                    Option(key="C", text="3/4 of total area"),
                    Option(key="D", text="1/3 of total area"),
                ),
                correct_key="A",
                explanation="1 of the 4 equal parts is shaded, representing 1/4.",
            ),
        ),
    )
    mock_repo.get_question_set.return_value = qset
    mock_repo.list_question_sets.return_value = (qset,)
    mock_repo.visible_question_sets.return_value = (qset,)
    mock_repo.profile_library_catalog.return_value = ()
    mock_repo.institute_work.return_value = ()
    mock_repo.find_in_progress_attempt.return_value = None
    mock_repo.list_attempts.return_value = ()
    mock_repo.get_student_account_context.return_value = {"cloud_account_id": "acc-01", "account_display_name": "Aksh"}

    def fake_get_setting(key):
        if key == "account_profiles":
            return '{"profiles": [{"local_profile_id": "prof-01"}, {"local_profile_id": "prof-02"}]}'
        if key == "network_state":
            return "online"
        return None
    mock_repo.get_setting.side_effect = fake_get_setting
    mock_repo.get_profile_pin.return_value = (None, None)

    prof1 = Profile(id="prof-01", display_name="Alex", cloud_account_id="acc-01", cloud_profile_id="c1", ownership_state="owned")
    prof2 = Profile(id="prof-02", display_name="Maya", cloud_account_id="acc-01", cloud_profile_id="c2", ownership_state="owned")
    mock_repo.list_profiles.return_value = (prof1, prof2)

    app_ctrl.startup_session.repository = mock_repo
    app_ctrl.startup_session.complete = True
    app_ctrl._initialize_runtime()

    engine = QQmlApplicationEngine()
    qml_dir = Path("app/ui_qt/qml").resolve()
    engine.addImportPath(str(qml_dir))

    prof_ctrl = ProfileController(app_ctrl)
    lib_ctrl = LibraryController(app_ctrl)
    assess_ctrl = AssessmentController(app_ctrl)
    settings_ctrl = SettingsController(app_ctrl)

    ctx = engine.rootContext()
    ctx.setContextProperty("appController", app_ctrl)
    ctx.setContextProperty("profileController", prof_ctrl)
    ctx.setContextProperty("libraryController", lib_ctrl)
    ctx.setContextProperty("assessmentController", assess_ctrl)
    ctx.setContextProperty("settingsController", settings_ctrl)

    engine.load(QUrl.fromLocalFile(str(qml_dir / "App.qml")))
    window = engine.rootObjects()[0]
    window.setWidth(800)
    window.setHeight(480)
    window.show()

    # Helper to grab current window surface
    def grab_and_save(filename):
        app.processEvents()
        image = window.grabWindow()
        path = output_dir / filename
        image.save(str(path))
        print(f"Captured {filename}: {image.width()}x{image.height()}")

    # 1. Startup screen
    app_ctrl.navigate("startup")
    grab_and_save("01_startup_800x480.png")

    # 2. Profile Picker
    app_ctrl.navigate("profile_picker")
    grab_and_save("02_profile_picker_800x480.png")

    # 3. Home Dashboard
    app_ctrl.navigate("home")
    grab_and_save("03_home_800x480.png")

    # 4. Subject Selection
    app_ctrl.navigate("subjects")
    grab_and_save("04_subjects_800x480.png")

    # 5. Test Setup
    app_ctrl.navigate("test_setup")
    grab_and_save("05_test_setup_800x480.png")

    # 6. Active Question
    assess_ctrl.startTest("practice", 10)
    grab_and_save("06_question_800x480.png")

    # 7. Confidence Rating
    app_ctrl.navigate("confidence")
    grab_and_save("07_confidence_800x480.png")

    # 8. Question Navigator
    app_ctrl.navigate("question_nav")
    grab_and_save("08_question_nav_800x480.png")

    # 9. Results
    assess_ctrl._result_cache = Mock(
        score=8.0,
        maximum=10.0,
        percentage=80.0,
        confidence_breakdown={Confidence.SURE: 6, Confidence.NOT_SURE: 3, Confidence.GUESSING: 1},
    )
    assess_ctrl.resultChanged.emit()
    app_ctrl.navigate("result")
    grab_and_save("09_result_800x480.png")

    # 10. Review Screen
    app_ctrl.navigate("review")
    grab_and_save("10_review_800x480.png")

    # 11. Practice & Downloads (Content)
    app_ctrl.navigate("content")
    grab_and_save("11_downloads_800x480.png")

    # 12. History
    app_ctrl.navigate("history")
    grab_and_save("12_history_800x480.png")

    # 13. Settings Overview
    app_ctrl.navigate("settings")
    grab_and_save("13_settings_800x480.png")

    # 14. Wi-Fi
    app_ctrl.navigate("wifi")
    grab_and_save("14_wifi_800x480.png")

    # 15. Diagnostics
    app_ctrl.navigate("diagnostics")
    grab_and_save("15_diagnostics_800x480.png")

    # 16. Device Pairing
    app_ctrl.navigate("pairing")
    grab_and_save("16_pairing_800x480.png")

    app_ctrl.close()
    print("All 16 development screenshots captured at exactly 800x480.")


if __name__ == "__main__":
    capture_all()
