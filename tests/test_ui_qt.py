"""Automated smoke and functional regression tests for the PySide6/QML UI."""

import os
from pathlib import Path
from unittest.mock import Mock

import pytest

# Ensure headless offscreen platform for CI/automated testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QSG_RENDER_LOOP"] = "basic"

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from app.auth.credentials import CredentialStore
from app.config import AppConfig
from app.core.models import Confidence, MarkingScheme, Option, Profile, Question, QuestionSet
from app.ui_qt.controllers.app_controller import AppController
from app.ui_qt.controllers.assessment_controller import AssessmentController
from app.ui_qt.controllers.library_controller import LibraryController
from app.ui_qt.controllers.profile_controller import ProfileController
from app.ui_qt.controllers.settings_controller import SettingsController


@pytest.fixture(scope="session")
def qapp():
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])
    yield app


@pytest.fixture
def mock_repo(tmp_path):
    repo = Mock()
    repo.schema_version = 8
    repo.get_or_create_device_id.return_value = "rpi-test-01"
    repo.quick_check.return_value = Mock(ok=True)
    repo.get_student_account_context.return_value = {
        "cloud_account_id": "acc-01",
        "account_display_name": "Aksh",
    }
    def fake_get_setting(key):
        if key == "account_profiles":
            return '{"profiles": [{"local_profile_id": "prof-01"}]}'
        if key == "network_state":
            return "online"
        return None
    repo.get_setting.side_effect = fake_get_setting
    repo.count_attempts_by_sync_status.return_value = 0
    repo.sync_diagnostic_summary.return_value = {"attention_required": False}
    repo.get_profile_pin.return_value = (None, None)

    profile = Profile(
        id="prof-01",
        display_name="Alex",
        cloud_account_id="acc-01",
        cloud_profile_id="cprof-01",
        ownership_state="owned",
    )
    repo.list_profiles.return_value = (profile,)

    qset = QuestionSet(
        id="bio-pack-01",
        version=1,
        title="Cell Structure",
        subject="Biology",
        chapter="Cells",
        marking=MarkingScheme(),
        questions=(
            Question(
                id="q1",
                position=1,
                topic="Fractions",
                difficulty=1,
                question_text="What fraction is shaded?",
                options=(
                    Option(key="A", text="1/4"),
                    Option(key="B", text="1/2"),
                    Option(key="C", text="3/4"),
                    Option(key="D", text="1/3"),
                ),
                correct_key="A",
            ),
        ),
    )
    repo.list_question_sets.return_value = (qset,)
    repo.get_question_set.return_value = qset
    repo.visible_question_sets.return_value = (qset,)
    repo.profile_library_catalog.return_value = ()
    repo.institute_work.return_value = ()
    repo.find_in_progress_attempt.return_value = None
    repo.list_attempts.return_value = ()
    repo.save_response.side_effect = lambda resp, *args, **kwargs: resp
    repo.create_attempt.return_value = Mock(id="att-01", profile_id="prof-01", set_id="bio-pack-01", set_version=1)
    return repo


def test_qml_app_loads(qapp, tmp_path, mock_repo):
    """Verify that App.qml and all components load cleanly into QQmlApplicationEngine."""
    db_path = tmp_path / "test.db"
    db_path.touch()

    config = AppConfig(database_path=db_path)
    creds = CredentialStore(tmp_path / "creds.json")

    engine = QQmlApplicationEngine()
    qml_dir = Path("app/ui_qt/qml").resolve()
    engine.addImportPath(str(qml_dir))

    app_ctrl = AppController(db_path, config, creds)
    # inject mock repo to avoid needing migrations during offscreen unit test
    app_ctrl.startup_session.repository = mock_repo
    app_ctrl.startup_session.complete = True
    app_ctrl._initialize_runtime()

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

    app_qml = qml_dir / "App.qml"
    engine.load(QUrl.fromLocalFile(str(app_qml)))

    assert len(engine.rootObjects()) > 0, "Failed to load App.qml root object"
    root_win = engine.rootObjects()[0]
    assert root_win.width() >= 800
    assert root_win.height() >= 480

    app_ctrl.close()


def test_navigation_and_controller_properties(qapp, tmp_path, mock_repo):
    """Verify routing and property transitions in controllers."""
    db_path = tmp_path / "test.db"
    db_path.touch()

    config = AppConfig(database_path=db_path)
    creds = CredentialStore(tmp_path / "creds.json")

    app_ctrl = AppController(db_path, config, creds)
    app_ctrl.startup_session.repository = mock_repo
    app_ctrl.startup_session.complete = True
    app_ctrl._initialize_runtime()

    assert app_ctrl.screen in {"profile_picker", "home", "pairing"}

    # Test navigation
    app_ctrl.navigate("home")
    assert app_ctrl.screen == "home"
    assert not app_ctrl.isAssessmentActive

    app_ctrl.navigate("subjects")
    assert app_ctrl.screen == "subjects"

    app_ctrl.navigate("question")
    assert app_ctrl.screen == "question"
    assert app_ctrl.isAssessmentActive  # NavRail should be hidden

    app_ctrl.goHome()
    assert app_ctrl.screen == "home"

    app_ctrl.close()


def test_profile_controller_listing_and_selection(qapp, tmp_path, mock_repo):
    db_path = tmp_path / "test.db"
    db_path.touch()

    config = AppConfig(database_path=db_path)
    creds = CredentialStore(tmp_path / "creds.json")

    app_ctrl = AppController(db_path, config, creds)
    app_ctrl.startup_session.repository = mock_repo
    app_ctrl.startup_session.complete = True
    app_ctrl._initialize_runtime()

    prof_ctrl = ProfileController(app_ctrl)
    assert prof_ctrl.profileCount >= 1
    assert prof_ctrl.canAddProfile is True

    prof_ctrl.selectProfile(0)
    assert app_ctrl.screen == "home"

    app_ctrl.close()


def test_library_and_assessment_properties(qapp, tmp_path, mock_repo):
    db_path = tmp_path / "test.db"
    db_path.touch()

    config = AppConfig(database_path=db_path)
    creds = CredentialStore(tmp_path / "creds.json")

    app_ctrl = AppController(db_path, config, creds)
    app_ctrl.startup_session.repository = mock_repo
    app_ctrl.startup_session.complete = True
    app_ctrl._initialize_runtime()

    lib_ctrl = LibraryController(app_ctrl)
    assert len(lib_ctrl.subjects) >= 1
    assert len(lib_ctrl.chapters) >= 1

    assess_ctrl = AssessmentController(app_ctrl)
    assert assess_ctrl.questionIndex == 1
    assert assess_ctrl.answeredCount == 0

    app_ctrl.close()


def test_assessment_flow_full(qapp, tmp_path, mock_repo):
    """Test full assessment interaction: start, select answer, confidence, submit, and review."""
    db_path = tmp_path / "test.db"
    db_path.touch()

    config = AppConfig(database_path=db_path)
    creds = CredentialStore(tmp_path / "creds.json")

    app_ctrl = AppController(db_path, config, creds)
    app_ctrl.startup_session.repository = mock_repo
    app_ctrl.startup_session.complete = True
    app_ctrl._initialize_runtime()

    assess_ctrl = AssessmentController(app_ctrl)

    # Mock application methods for active assessment
    mock_app = Mock()
    app_ctrl.ui_controller.application = mock_app
    mock_question = mock_repo.get_question_set("bio-pack-01", 1).questions[0]
    mock_app.current_question.return_value = mock_question
    mock_app.current_response.return_value = Mock(selected_key="A", marked_review=False)

    assess_ctrl.startTest("practice", 10)
    assert assess_ctrl.isActive
    assert assess_ctrl.timerEnabled
    assert assess_ctrl.remainingSeconds == 600

    # Select answer
    assess_ctrl.selectAnswer("A")
    mock_app.select_answer.assert_called_with("A")

    # Set confidence
    assess_ctrl.setConfidence("sure")
    mock_app.set_confidence.assert_called()

    # Toggle review
    assess_ctrl.toggleMarkReview()
    mock_app.set_marked_review.assert_called_with(True)

    # Submit
    mock_app.submit.return_value = Mock(
        score=4.0,
        maximum=4.0,
        percentage=100.0,
        confidence_breakdown={Confidence.SURE: 1},
    )
    assess_ctrl.confirmSubmit()
    assert assess_ctrl.scorePercent == 100
    assert not assess_ctrl.isActive

    app_ctrl.close()


def test_settings_controller_operations(qapp, tmp_path, mock_repo):
    """Test SettingsController Wi-Fi, Sync, Update, and Diagnostics triggers."""
    db_path = tmp_path / "test.db"
    db_path.touch()

    config = AppConfig(database_path=db_path)
    creds = CredentialStore(tmp_path / "creds.json")

    app_ctrl = AppController(db_path, config, creds)
    app_ctrl.startup_session.repository = mock_repo
    app_ctrl.startup_session.complete = True
    app_ctrl._initialize_runtime()

    settings_ctrl = SettingsController(app_ctrl)
    assert len(settings_ctrl.availableNetworks) >= 1
    assert settings_ctrl.overallHealth == "Everything looks good!"
    assert settings_ctrl.storageUsedGb > 0
    assert settings_ctrl.storageTotalGb > 0

    # Trigger async jobs (non-blocking)
    settings_ctrl.scanWifi()
    settings_ctrl.startSync()
    settings_ctrl.checkUpdate()
    settings_ctrl.runDiagnostics()

    app_ctrl.close()


def test_responsive_window_sizing(qapp, tmp_path, mock_repo):
    """Verify QML layout responsiveness at 800x480 and 800x600."""
    db_path = tmp_path / "test.db"
    db_path.touch()

    config = AppConfig(database_path=db_path)
    creds = CredentialStore(tmp_path / "creds.json")

    engine = QQmlApplicationEngine()
    qml_dir = Path("app/ui_qt/qml").resolve()
    engine.addImportPath(str(qml_dir))

    app_ctrl = AppController(db_path, config, creds)
    app_ctrl.startup_session.repository = mock_repo
    app_ctrl.startup_session.complete = True
    app_ctrl._initialize_runtime()

    ctx = engine.rootContext()
    ctx.setContextProperty("appController", app_ctrl)
    ctx.setContextProperty("profileController", ProfileController(app_ctrl))
    ctx.setContextProperty("libraryController", LibraryController(app_ctrl))
    ctx.setContextProperty("assessmentController", AssessmentController(app_ctrl))
    ctx.setContextProperty("settingsController", SettingsController(app_ctrl))

    engine.load(QUrl.fromLocalFile(str(qml_dir / "App.qml")))
    assert len(engine.rootObjects()) > 0
    win = engine.rootObjects()[0]

    # Target 1: 800 x 480
    win.setWidth(800)
    win.setHeight(480)
    assert win.width() == 800
    assert win.height() == 480

    # Target 2: 800 x 600 (dev fallback)
    win.setWidth(800)
    win.setHeight(600)
    assert win.width() == 800
    assert win.height() == 600

    app_ctrl.close()


def test_all_qml_screens_compile_cleanly(qapp, tmp_path, mock_repo):
    """Verify that every single QML screen component compiles with zero errors."""
    from PySide6.QtQml import QQmlComponent

    db_path = tmp_path / "test_screens.db"
    db_path.touch()
    config = AppConfig(database_path=db_path)
    creds = CredentialStore(tmp_path / "creds.json")

    engine = QQmlApplicationEngine()
    qml_dir = Path("app/ui_qt/qml").resolve()
    engine.addImportPath(str(qml_dir))

    app_ctrl = AppController(db_path, config, creds)
    app_ctrl.startup_session.repository = mock_repo
    app_ctrl.startup_session.complete = True
    app_ctrl._initialize_runtime()

    ctx = engine.rootContext()
    ctx.setContextProperty("appController", app_ctrl)
    ctx.setContextProperty("profileController", ProfileController(app_ctrl))
    ctx.setContextProperty("libraryController", LibraryController(app_ctrl))
    ctx.setContextProperty("assessmentController", AssessmentController(app_ctrl))
    ctx.setContextProperty("settingsController", SettingsController(app_ctrl))

    screens_dir = qml_dir / "screens"
    for qml_path in screens_dir.glob("*.qml"):
        comp = QQmlComponent(engine, QUrl.fromLocalFile(str(qml_path)))
        assert not comp.isError(), f"Compilation error in {qml_path.name}: {[e.toString() for e in comp.errors()]}"

    app_ctrl.close()


def test_navigation_routes_and_error_boundary(qapp, tmp_path, mock_repo):
    """Verify navigating across all reported routes loads without Loader error."""
    from PySide6.QtCore import QCoreApplication

    db_path = tmp_path / "test_routes.db"
    db_path.touch()
    config = AppConfig(database_path=db_path)
    creds = CredentialStore(tmp_path / "creds.json")

    engine = QQmlApplicationEngine()
    qml_dir = Path("app/ui_qt/qml").resolve()
    engine.addImportPath(str(qml_dir))

    app_ctrl = AppController(db_path, config, creds)
    app_ctrl.startup_session.repository = mock_repo
    app_ctrl.startup_session.complete = True
    app_ctrl._initialize_runtime()

    ctx = engine.rootContext()
    ctx.setContextProperty("appController", app_ctrl)
    ctx.setContextProperty("profileController", ProfileController(app_ctrl))
    ctx.setContextProperty("libraryController", LibraryController(app_ctrl))
    ctx.setContextProperty("assessmentController", AssessmentController(app_ctrl))
    ctx.setContextProperty("settingsController", SettingsController(app_ctrl))

    engine.load(QUrl.fromLocalFile(str(qml_dir / "App.qml")))
    assert len(engine.rootObjects()) > 0
    win = engine.rootObjects()[0]
    screen_loader = win.findChild(object, "screenLoader")

    # Test all reported routes
    routes_to_test = [
        "home",
        "library",
        "subjects",
        "chapters",
        "packs",
        "test_setup",
        "practice",
        "content",
        "history",
        "settings",
        "wifi",
        "sync",
        "account",
        "diagnostics",
        "software_update",
        "device_info",
        "about",
    ]

    for route in routes_to_test:
        app_ctrl.navigate(route)
        QCoreApplication.processEvents()
        if screen_loader is not None:
            # Loader status: 1 is Ready, 0 is Null, 3 is Error
            assert screen_loader.property("status") != 3, f"Screen Loader Error for route '{route}'"

    app_ctrl.close()


def test_offline_pack_to_question_flow(qapp, tmp_path, mock_repo):
    """Verify offline downloaded pack -> test setup -> start test -> question -> answers."""
    db_path = tmp_path / "test_flow.db"
    db_path.touch()
    config = AppConfig(database_path=db_path)
    creds = CredentialStore(tmp_path / "creds.json")

    app_ctrl = AppController(db_path, config, creds)
    app_ctrl.startup_session.repository = mock_repo
    app_ctrl.startup_session.complete = True
    app_ctrl._initialize_runtime()

    lib_ctrl = LibraryController(app_ctrl)
    assess_ctrl = AssessmentController(app_ctrl)

    # 1. Select downloaded pack
    lib_ctrl.selectPack("bio-pack-01", 1)
    assert app_ctrl.screen == "test_setup"

    # 2. Start Test
    assess_ctrl.startTest(mode="practice", timer_minutes=0)
    assert app_ctrl.screen == "question"
    assert assess_ctrl.isActive
    assert assess_ctrl.questionText == "What fraction is shaded?"
    assert len(assess_ctrl.options) == 4

    # 3. Answer question
    assess_ctrl.selectAnswer("A")
    assert any(opt["selected"] and opt["key"] == "A" for opt in assess_ctrl.options)

    app_ctrl.close()

