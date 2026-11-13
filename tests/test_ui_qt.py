"""Automated smoke and functional regression tests for the PySide6/QML UI."""

import os
from pathlib import Path
from unittest.mock import Mock

import pytest

# Ensure headless offscreen platform for CI/automated testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QSG_RENDER_LOOP"] = "basic"
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from app.auth.credentials import CredentialStore
from app.config import AppConfig
from app.core.models import (
    Attempt,
    AttemptStatus,
    Confidence,
    MarkingScheme,
    Option,
    Profile,
    Question,
    QuestionSet,
    Response,
)
from app.data.repo import SyncStatus
from app.ui.controller import HistoryItem
from app.ui_qt.controllers.app_controller import AppController
from app.ui_qt.controllers.assessment_controller import AssessmentController
from app.ui_qt.controllers.library_controller import LibraryController
from app.ui_qt.controllers.profile_controller import ProfileController
from app.ui_qt.controllers.quick_add_controller import QuickAddController
from app.ui_qt.controllers.settings_controller import SettingsController


@pytest.fixture(scope="session")
def qapp():
    QQuickStyle.setStyle("Basic")
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
        link_state="linked",
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
    repo.completed_results.return_value = []
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
    quick_add_ctrl = QuickAddController(app_ctrl)

    ctx = engine.rootContext()
    ctx.setContextProperty("appController", app_ctrl)
    ctx.setContextProperty("profileController", prof_ctrl)
    ctx.setContextProperty("libraryController", lib_ctrl)
    ctx.setContextProperty("assessmentController", assess_ctrl)
    ctx.setContextProperty("settingsController", settings_ctrl)
    ctx.setContextProperty("quickAddController", quick_add_ctrl)

    app_qml = qml_dir / "App.qml"
    engine.load(QUrl.fromLocalFile(str(app_qml)))

    assert len(engine.rootObjects()) > 0, "Failed to load App.qml root object"
    root_win = engine.rootObjects()[0]
    assert root_win.width() == 800
    assert root_win.height() == 480

    # Render the real illustrated practice setup at the target panel resolution.
    lib_ctrl._selected_pack_id = "bio-pack-01"
    lib_ctrl._selected_pack_version = 1
    lib_ctrl.selectionChanged.emit()
    app_ctrl.navigate("test_setup")
    root_win.show()
    qapp.processEvents()
    frame = qapp.primaryScreen().grabWindow(root_win.winId())
    assert not frame.isNull(), "QML setup screen did not render"
    assert (frame.width(), frame.height()) == (800, 480)
    assert frame.save(str(tmp_path / "practice-setup-800x480.png"))

    app_ctrl.navigate("quick_add")
    qapp.processEvents()
    quick_add_frame = qapp.primaryScreen().grabWindow(root_win.winId())
    assert not quick_add_frame.isNull()
    assert (quick_add_frame.width(), quick_add_frame.height()) == (800, 480)

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


def test_external_browser_history_commit_refreshes_rendered_qt_model(qapp, tmp_path):
    """A background SQLite commit appears in the existing History screen without restart."""
    import json
    from uuid import uuid4

    from PySide6.QtGui import QFont, QFontDatabase
    from PySide6.QtQuick import QQuickWindow

    from app.data.repo import Repository

    # The offscreen Windows plugin has no system font fallback; load one for render QA.
    if os.name == "nt":
        font_path = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/segoeui.ttf"
        assert QFontDatabase.addApplicationFont(str(font_path)) >= 0
        QFont.insertSubstitution("system-ui", "Segoe UI")
        qapp.setFont(QFont("Segoe UI"))
    account, profile, link, result_id = (str(uuid4()) for _ in range(4))
    local = "cloud-" + profile
    path = tmp_path / "history.db"
    repo = Repository(path)
    repo.create_profile(Profile(local, "Student", cloud_account_id=account,
        cloud_profile_id=profile, ownership_state="owned", link_state="unlinked"))
    repo.apply_profile_link(local, {"status": "linked", "link_id": link,
        "student_account_id": account, "study_profile_id": profile, "local_profile_id": local,
        "account_display_name": "Student", "study_profile_name": "Student"})
    repo.cache_student_account_context(account, "Student")
    repo.set_setting("account_profiles", json.dumps({"profiles": [{"local_profile_id": local}]}))
    config = AppConfig(database_path=path)
    app_ctrl = AppController(path, config, CredentialStore(tmp_path / "creds"))
    app_ctrl.startup_session.repository = repo
    app_ctrl.startup_session.complete = True
    app_ctrl._initialize_runtime()
    prof = ProfileController(app_ctrl)
    library = LibraryController(app_ctrl)
    assessment = AssessmentController(app_ctrl)
    settings = SettingsController(app_ctrl)
    engine = QQmlApplicationEngine()
    root = Path("app/ui_qt/qml").resolve()
    engine.addImportPath(str(root))
    for name, controller in (("appController", app_ctrl), ("profileController", prof),
            ("libraryController", library), ("assessmentController", assessment),
            ("settingsController", settings)):
        engine.rootContext().setContextProperty(name, controller)
    engine.load(QUrl.fromLocalFile(str(root / "App.qml")))
    assert engine.rootObjects()
    app_ctrl.navigate("history")
    app_ctrl._on_tick()
    changed = []
    assessment.historyChanged.connect(lambda: changed.append(True))
    with Repository(path) as worker_repo:
        worker_repo.set_setting("last_full_sync", json.dumps({"at": "2026-10-30T10:02:00Z",
            "result": "Up to date", "profiles": {"available": 1, "retired": 1},
            "stages": {"history": "OK", "content": "OK", "heartbeat": "OK",
                       "attempt_uploads": {"uploaded": 0, "failed": 0}}}))
        worker_repo.cache_completed_results(local, link, [{
            "attempt_id": result_id, "study_profile_id": profile, "source": "web",
            "status": "completed", "title": "Browser completion", "subject": "Biology",
            "started_at": "2026-10-30T10:00:00Z", "completed_at": "2026-10-30T10:01:00Z",
            "result": {"score": 4, "maximum_score": 8, "correct": 1, "wrong": 0,
                       "skipped": 1, "duration_ms": 60000, "response_time_ms": 30000,
                       "confidence": {"sure": {"total": 1, "correct": 1, "wrong": 0},
                                      "not_sure": {"total": 0, "correct": 0, "wrong": 0},
                                      "guessing": {"total": 0, "correct": 0, "wrong": 0},
                                      "unrated": {"total": 0, "correct": 0, "wrong": 0}}}}])
    app_ctrl._on_tick()
    qapp.processEvents()
    assert changed
    assert assessment.historyList[0]["title"] == "Browser completion"
    assert assessment.historyList[0]["synced"] is True
    assert assessment.historyAnalytics["attempts"] == 1
    assert assessment.historyAnalytics["correct"] == 1
    assert assessment.historyAnalytics["skipped"] == 1
    assert assessment.historyAnalytics["practiceTimeMs"] == 60000
    assert assessment.historyAnalytics["confidence"]["sure"] == {"correct": 1, "wrong": 0}
    assert assessment.historyAnalytics["trends"][0]["accuracyPercent"] == 100
    assert repo.get_attempt(result_id) is None
    window = engine.rootObjects()[0]
    assert isinstance(window, QQuickWindow)
    assert (window.width(), window.height()) == (800, 480)
    app_ctrl.navigate("progress")
    qapp.processEvents()
    assert assessment.historyAnalytics["attempts"] == 1
    progress_image = window.grabWindow()
    assert not progress_image.isNull()
    assert progress_image.save(str(tmp_path / "progress-analytics-800x480.png"))
    app_ctrl.navigate("history")
    qapp.processEvents()
    image = window.grabWindow()
    assert not image.isNull()
    assert image.save(str(tmp_path / "history-down-sync.png"))
    assert next(item for item in settings.diagnosticItems if item["name"] == "Last Full Sync")["status"] == "Up to date"
    app_ctrl.navigate("diagnostics")
    qapp.processEvents()
    assert window.grabWindow().save(str(tmp_path / "sync-diagnostics.png"))
    app_ctrl.close()


def test_cloud_echo_of_local_attempt_is_counted_once(tmp_path):
    """A Pi upload echoed by cloud History stays one local analytics entry."""
    import json
    from datetime import UTC, datetime, timedelta
    from uuid import uuid4

    from app.data.repo import Repository

    account, profile_id, link_id, attempt_id = (str(uuid4()) for _ in range(4))
    local_profile_id = "local-" + profile_id
    path = tmp_path / "deduplicated-history.db"
    completed_at = datetime.now(UTC)
    started_at = completed_at - timedelta(minutes=2)
    repo = Repository(path)
    repo.create_profile(Profile(local_profile_id, "Student", cloud_account_id=account,
        cloud_profile_id=profile_id, ownership_state="owned", link_state="unlinked"))
    repo.apply_profile_link(local_profile_id, {"status": "linked", "link_id": link_id,
        "student_account_id": account, "study_profile_id": profile_id,
        "local_profile_id": local_profile_id, "account_display_name": "Student",
        "study_profile_name": "Student"})
    qset = QuestionSet("local-pack", 1, "Local practice", "Biology", "Cells",
        MarkingScheme(), (Question("q1", 1, "Cells", 1, "Question?",
            (Option("A", "Yes"), Option("B", "No"), Option("C", "Maybe"), Option("D", "None")),
            "A"),))
    repo.import_question_set(qset, content_hash="sha256:local", downloaded_at=started_at,
        is_active=True)
    repo.create_attempt(Attempt(attempt_id, local_profile_id, qset.id, qset.version,
        AttemptStatus.IN_PROGRESS, started_at), question_order=("q1",))
    repo.save_response(Response("response-1", attempt_id, "q1", "A", Confidence.SURE),
        is_correct=True, answered_at=completed_at)
    repo.complete_attempt(attempt_id, completed_at=completed_at, duration_ms=120000, score=4)
    repo.cache_completed_results(local_profile_id, link_id, [{
        "attempt_id": attempt_id, "study_profile_id": profile_id, "source": "device",
        "status": "completed", "title": "Local practice", "subject": "Biology",
        "started_at": started_at.isoformat(), "completed_at": completed_at.isoformat(),
        "result": {"score": 4, "maximum_score": 4, "correct": 1, "wrong": 0,
            "skipped": 0, "duration_ms": 120000, "response_time_ms": 30000,
            "confidence": {"sure": {"total": 1, "correct": 1, "wrong": 0}}},
    }])
    repo.set_setting("account_profiles", json.dumps({"profiles": [
        {"local_profile_id": local_profile_id}]}))
    app_ctrl = AppController(path, AppConfig(database_path=path),
        CredentialStore(tmp_path / "dedup-creds.json"))
    app_ctrl.startup_session.repository = repo
    app_ctrl.startup_session.complete = True
    app_ctrl._initialize_runtime()
    assessment = AssessmentController(app_ctrl)

    assert len(assessment.historyList) == 1
    assert assessment.historyList[0]["source"] == "device"
    assert assessment.historyAnalytics["attempts"] == 1
    assert assessment.historyAnalytics["correct"] == 1
    assert assessment.historyAnalytics["confidence"]["sure"]["correct"] == 1

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
    assert settings_ctrl.overallHealth == app_ctrl.networkLabel
    assert settings_ctrl.storageUsedGb > 0
    assert settings_ctrl.storageTotalGb > 0

    # Trigger async jobs (non-blocking)
    settings_ctrl.scanWifi()
    settings_ctrl.startSync()
    settings_ctrl.checkUpdate()
    settings_ctrl.runDiagnostics()

    app_ctrl.close()


def test_update_controller_binds_signed_release_and_actions(qapp, tmp_path, mock_repo):
    from types import SimpleNamespace

    from packaging.version import Version

    db_path = tmp_path / "update-controller.db"
    db_path.touch()
    app_ctrl = AppController(db_path, AppConfig(database_path=db_path), CredentialStore(tmp_path / "creds.json"))
    app_ctrl.startup_session.repository = mock_repo
    app_ctrl.startup_session.complete = True
    app_ctrl._initialize_runtime()
    mock_repo.schema_version = 8
    manifest = SimpleNamespace(
        version=Version("0.2.0"),
        data={
            "compatibility": {"platform": "linux", "architecture": "aarch64"},
            "release": {"required_db_schema": 8, "notes": "Stability improvements"},
        },
    )
    release = SimpleNamespace(manifest=manifest)
    app_ctrl.device.available_update = release
    calls = []
    app_ctrl.device.start = lambda operation, **kwargs: calls.append((operation, kwargs))
    settings = SettingsController(app_ctrl)

    assert settings.hasUpdate
    assert settings.updateCompatible
    assert settings.availableVersion == "0.2.0"
    assert settings.updateNotes == "Stability improvements"
    settings.checkUpdate()
    settings.downloadUpdate()
    assert [operation for operation, _kwargs in calls] == ["update_check", "update_download"]
    assert calls[-1][1]["update"] is release
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
    """Instantiate all screens, reusable components and App; catch asset warnings."""
    from PySide6.QtCore import QEvent, qInstallMessageHandler
    from PySide6.QtQml import QQmlComponent

    db_path = tmp_path / "test_screens.db"
    config = AppConfig(database_path=db_path)
    creds = CredentialStore(tmp_path / "creds.json")
    engine = QQmlApplicationEngine()
    qml_dir = Path("app/ui_qt/qml").resolve()
    engine.addImportPath(str(qml_dir))
    app_ctrl = AppController(db_path, config, creds)
    app_ctrl.startup_session.repository = mock_repo
    app_ctrl.startup_session.complete = True
    app_ctrl._initialize_runtime()
    controllers = {
        "appController": app_ctrl,
        "profileController": ProfileController(app_ctrl),
        "libraryController": LibraryController(app_ctrl),
        "assessmentController": AssessmentController(app_ctrl),
        "settingsController": SettingsController(app_ctrl),
    }
    for name, controller in controllers.items():
        engine.rootContext().setContextProperty(name, controller)
    warnings = []
    engine.warnings.connect(lambda errors: warnings.extend(e.toString() for e in errors))
    previous = qInstallMessageHandler(lambda kind, context, message: warnings.append(message))
    paths = sorted((qml_dir / "screens").glob("*.qml"))
    paths += sorted((qml_dir / "components").glob("*.qml"))
    paths += [qml_dir / "App.qml"]
    try:
        for path in paths:
            component = QQmlComponent(engine, QUrl.fromLocalFile(str(path)))
            assert not component.isError(), [e.toString() for e in component.errors()]
            obj = component.create()
            assert obj is not None, [e.toString() for e in component.errors()]
            qapp.processEvents()
            obj.deleteLater()
            qapp.sendPostedEvents(None, QEvent.DeferredDelete)
        failures = [message for message in warnings if any(
            marker in message.lower() for marker in
            ("cannot open", "cannot load", "file not found", "qqmlcomponent", "qml loader error")
        )]
        assert not failures, "\n".join(failures)
    finally:
        qInstallMessageHandler(previous)
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



def test_background_removal_refreshes_qt_models_and_session(qapp, tmp_path):
    from app.content.importer import import_pack
    from app.data.repo import Repository
    from tests.content.test_profile_library import metadata, setup

    path = tmp_path / "reconciliation.db"
    with Repository(path) as repo:
        link = setup(repo)
        pack = import_pack(Path("content/sample_biology.json"), repo).pack.question_set
        repo.cache_profile_library("a", link, [metadata(Path("content/sample_biology.json").read_bytes())])
        ctrl = AppController(path, AppConfig(database_path=path), CredentialStore(tmp_path / "creds.json"))
        ctrl.startup_session.repository = repo
        ctrl.startup_session.complete = True
        ctrl._initialize_runtime()
        library = LibraryController(ctrl)
        assessment = AssessmentController(ctrl)
        library.selectSubject(pack.subject)
        library.selectChapter(pack.chapter)
        library.selectPack(pack.id, pack.version)
        attempt = ctrl.ui_controller.application.start_test("a", pack.id, pack.version)
        assessment._active = True
        ctrl.navigate("question")
        ctrl._on_tick()
        changes = []
        library.catalogChanged.connect(lambda: changes.append(True))
        with Repository(path) as background:
            background.cache_profile_library("a", link, [])
        ctrl._on_tick()
        assert changes
        assert library.packs == []
        assert library.selectedPack == {}
        assert library._selected_pack_id == ""
        assert not library.canResume
        assert not assessment.isActive
        assert ctrl.ui_controller.application.engine.attempt is None
        assert repo.get_attempt(attempt.id).status.value == "abandoned"
        assert ctrl.screen == "home"
        ctrl.close()


def test_runtime_switch_isolates_profile_state_and_preserves_offline_attempts(qapp, tmp_path):
    import json

    from app.assessment import AssessmentApplication
    from app.connectivity import record_cloud
    from app.content.importer import import_pack
    from app.data.repo import Repository
    from tests.content.test_profile_library import metadata, setup

    path = tmp_path / "switch.db"
    with Repository(path) as repo:
        link_a = setup(repo)
        data = Path("content/sample_biology.json").read_bytes()
        pack_a = import_pack(Path("content/sample_biology.json"), repo).pack.question_set
        other = json.loads(data)
        other["set"]["id"] = "maya-biology"
        other["set"]["title"] = "Maya Biology"
        file_b = tmp_path / "b.json"
        file_b.write_text(json.dumps(other), encoding="utf-8")
        pack_b = import_pack(file_b, repo).pack.question_set
        repo.cache_profile_library("a", link_a, [metadata(data)])
        repo.cache_profile_library("b", repo.get_profile_link_context("b")["link_id"],
                                   [metadata(file_b.read_bytes())])
        for profile, pack in (("a", pack_a), ("b", pack_b)):
            service = AssessmentApplication(repo)
            service.start_test(profile, pack.id, 1)
            service.request_submit()
            service.submit()
        ctrl = AppController(path, AppConfig(database_path=path), CredentialStore(tmp_path / "cred.json"))
        ctrl.startup_session.repository = repo
        ctrl.startup_session.complete = True
        ctrl._initialize_runtime()
        profiles = ProfileController(ctrl)
        library = LibraryController(ctrl)
        assessment = AssessmentController(ctrl)
        settings = SettingsController(ctrl)
        profiles.selectProfile(0)
        assert ctrl.screen == "home"
        assert ctrl.activeProfileName == "Student A"
        attempt = ctrl.ui_controller.application.start_test("a", pack_a.id, 1)
        ctrl.ui_controller.application.select_answer("A")
        ctrl.ui_controller.application.continue_unrated()
        library.selectSubject(pack_a.subject)
        library.selectChapter(pack_a.chapter)
        library.selectPack(pack_a.id, 1)
        ctrl.goHome()
        record_cloud(path, "Offline")
        profiles.switchProfile()
        assert profiles.switchMode and ctrl.screen == "profile_picker"
        profiles.selectProfile(1)
        assert ctrl.screen == "home" and ctrl.activeProfileName == "Student B"
        assert ctrl.networkLabel == settings.cloudStatus == "Offline"
        assert {p["id"] for p in settings.installedPacks} == {pack_b.id}
        assert {p.id for p in ctrl.ui_controller.question_sets} == {pack_b.id}
        assert library._selected_pack_id == ""
        assert ctrl.ui_controller.application.engine.attempt is None
        assert not library.canResume
        assert len(assessment.historyList) == 1
        assert assessment.historyList[0]["title"] == "Maya Biology"
        assert assessment.historyAnalytics["attempts"] == 1
        assert assessment.historyAnalytics["deviceAttempts"] == 1
        assert assessment.historyAnalytics["correct"] == 0
        assert assessment.historyAnalytics["skipped"] == len(pack_b.questions)
        assert assessment.historyAnalytics["accuracyPercent"] == -1
        assert repo.find_in_progress_attempt("a").id == attempt.id
        assert repo.get_setting("last_active_profile_id") == "b"
        profiles.switchProfile()
        profiles.cancelSwitch()
        assert ctrl.activeProfileName == "Student B" and ctrl.screen == "home"
        profiles.switchProfile()
        profiles.selectProfile(0)
        assert library.canResume
        assert ctrl.ui_controller.application.resume_attempt("a").id == attempt.id
        assert repo.get_attempt_responses(attempt.id)[0].selected_key == "A"
        ctrl.navigate("question")
        profiles.switchProfile()
        profiles.selectProfile(1)
        assert ctrl.activeProfileName == "Student A" and ctrl.screen == "question"
        ctrl.goHome()
        profiles.switchProfile()
        profiles.selectProfile(1)
        # A complete cloud snapshot archives B while it was selected.
        repo.set_setting("account_profiles", json.dumps({"profiles": [{"local_profile_id": "a"}]}))
        ctrl._on_tick()
        assert ctrl.screen == "profile_picker"
        assert [p["id"] for p in profiles.profiles] == ["a"]
        profiles.selectProfile(1)
        assert ctrl.screen == "profile_picker"
        ctrl.close()


def test_authenticated_contact_notifies_header_and_settings_without_restart(qapp, tmp_path):
    import httpx

    from app.api.client import DeviceApi
    from app.auth.credentials import DeviceCredential
    from app.data.repo import Repository

    path = tmp_path / "status.db"
    config = AppConfig(database_path=path, api_base_url="https://cloud.test")
    store = CredentialStore(tmp_path / "credentials.json")
    store.save(DeviceCredential("device", "token"))
    with Repository(path) as repo:
        ctrl = AppController(path, config, store)
        ctrl.device.start = lambda *args, **kwargs: None
        ctrl.startup_session.repository = repo
        ctrl.startup_session.complete = True
        ctrl._initialize_runtime()
        settings = SettingsController(ctrl)
        notifications = []
        settings.wifiChanged.connect(lambda: notifications.append(True))
        ctrl._on_tick()
        notifications.clear()
        api = DeviceApi(config, store=store, transport=httpx.MockTransport(lambda request:
            httpx.Response(200, json={"schema_version": 1, "packs": []})))
        with api.content() as client:
            client.fetch_catalog()
        ctrl._on_tick()
        assert notifications
        assert ctrl.networkLabel == settings.cloudStatus == "Online"
        assert ctrl.isOnline
        ctrl.close()


def test_last_profile_highlight_and_revoked_pin_target(qapp, tmp_path):
    import hashlib

    from app.data.repo import Repository
    from tests.content.test_profile_library import setup

    path = tmp_path / "profiles.db"
    with Repository(path) as repo:
        setup(repo)
        repo.set_setting("last_active_profile_id", "b")
        digest = hashlib.pbkdf2_hmac("sha256", b"1234", b"salt", 100000).hex()
        repo._connection.execute("UPDATE profiles SET pin_hash=?, pin_salt='salt' WHERE id='a'",
                                 ("pbkdf2_sha256$100000$" + digest,))
        ctrl = AppController(path, AppConfig(database_path=path), CredentialStore(tmp_path / "creds.json"))
        ctrl.startup_session.repository = repo
        ctrl.startup_session.complete = True
        ctrl._initialize_runtime()
        profiles = ProfileController(ctrl)
        assert ctrl.ui_controller.selected_profile.id == "b"
        assert ctrl.screen == "profile_picker"  # Highlight only; preserve shared-device picker.
        profiles.selectProfileId("a")
        assert profiles.pinLocked
        profiles.submitPin("1234")
        assert ctrl.activeProfileName == "Student A" and ctrl.screen == "home"
        profiles.switchProfile()
        profiles.selectProfileId("a")
        assert profiles.pinLocked
        context = repo.get_profile_link_context("a")
        p = repo.get_profile("a")
        repo.apply_profile_link("a", {"status": "revoked", "local_profile_id": "a",
            "link_id": context["link_id"], "student_account_id": p.cloud_account_id,
            "study_profile_id": p.cloud_profile_id, "account_display_name": "Account",
            "study_profile_name": "A"})
        profiles.submitPin("1234")
        assert not profiles.pinLocked
        assert [p["id"] for p in profiles.profiles] == ["b"]
        profiles.selectProfileId("a")
        assert ctrl.screen == "profile_picker"
        ctrl.close()

    with Repository(path) as repo:
        ctrl = AppController(path, AppConfig(database_path=path), CredentialStore(tmp_path / "creds.json"))
        ctrl.startup_session.repository = repo
        ctrl.startup_session.complete = True
        ctrl._initialize_runtime()
        assert ctrl.screen == "profile_picker"
        assert ctrl.ui_controller.selected_profile.id == "b"
        ctrl.close()


def test_auto_sync_toggle_persists_and_manual_sync_remains_available(qapp, tmp_path):
    from unittest.mock import Mock

    from app.data.repo import Repository

    path = tmp_path / "toggle.db"
    with Repository(path) as repo:
        ctrl = AppController(path, AppConfig(database_path=path), CredentialStore(tmp_path / "creds.json"))
        ctrl.repository = repo
        settings = SettingsController(ctrl)
        assert settings.automaticSync
        settings.setAutomaticSync(False)
        assert not settings.automaticSync
        assert settings.nextAutomaticSync == "Off"
        ctrl.device.start = Mock()
        settings.startSync()
        ctrl.device.start.assert_called_once_with("sync")
        assert repo.get_setting("automatic_sync") == "0"
        ctrl._poll_timer.stop()
    with Repository(path) as repo:
        assert repo.get_setting("automatic_sync") == "0"


def test_local_profile_creation_and_testing_mode(qapp, tmp_path):
    """Verify local profile creation and testing mode work offline without cloud pairing."""
    from app.data.repo import Repository

    db_path = tmp_path / "offline_profile.db"
    with Repository(db_path) as repo:
        ctrl = AppController(db_path, AppConfig(database_path=db_path), CredentialStore(tmp_path / "creds.json"))
        ctrl.startup_session.repository = repo
        ctrl.startup_session.complete = True
        ctrl._initialize_runtime()

        prof_ctrl = ProfileController(ctrl)

        # Signal test
        received_text = []
        ctrl.keyboardSubmitted.connect(lambda text: received_text.append(text))
        ctrl.submitKeyboard("Test Student")
        assert received_text == ["Test Student"]
        assert not ctrl.keyboardVisible

        # Create local profile directly
        prof_ctrl.createProfile("Alice Learner", "Primary 5")
        assert any(p["name"] == "Alice Learner" for p in prof_ctrl.profiles)
        assert ctrl.activeProfileName == "Alice Learner"
        assert ctrl.screen == "home"

        # Testing mode quick start
        prof_ctrl.startTestingMode()
        assert ctrl.screen == "home"
        assert ctrl.activeProfileName != ""

        ctrl.close()


def test_history_items_preserve_web_or_device_source(qapp):
    app = Mock()
    app.ui_controller.history_items = (
        HistoryItem("Web practice", "Biology", 8, 10, None, SyncStatus.SYNCED, "web",
                    correct=6, wrong=2, skipped=2, duration_ms=120000, response_time_ms=60000),
        HistoryItem("Pi practice", "Biology", 7, 10, None, SyncStatus.PENDING,
                    correct=4, wrong=2, skipped=4, duration_ms=180000, response_time_ms=90000),
    )
    controller = AssessmentController(app)

    history = controller.historyList

    assert [item["source"] for item in history] == ["web", "device"]
    assert [item["scorePercent"] for item in history] == [80, 70]
    assert controller.historyAnalytics == {
        "attempts": 2,
        "correct": 10,
        "wrong": 4,
        "skipped": 6,
        "accuracyPercent": 71,
        "practiceTimeMs": 300000,
        "averageResponseTimeMs": 10714,
        "webAttempts": 1,
        "deviceAttempts": 1,
        "confidence": {
            "sure": {"correct": 0, "wrong": 0},
            "not_sure": {"correct": 0, "wrong": 0},
            "guessing": {"correct": 0, "wrong": 0},
            "unrated": {"correct": 0, "wrong": 0},
        },
        "trends": [
            {"index": 0, "label": "", "accuracyPercent": 67, "correct": 4, "wrong": 2},
            {"index": 1, "label": "", "accuracyPercent": 75, "correct": 6, "wrong": 2},
        ],
    }
    controller._countdown_timer.stop()


def test_history_analytics_window_and_cloud_answer_time_denominator(qapp):
    attempts = [
        HistoryItem(f"Attempt {index}", "Biology", 4, 8, None, SyncStatus.SYNCED,
                    "web", correct=1, wrong=1, skipped=1, duration_ms=1000,
                    response_time_ms=10000, answered=2)
        for index in range(21)
    ]
    app = Mock()
    app.ui_controller.history_items = tuple(attempts)
    controller = AssessmentController(app)

    assert controller.analyticsWindow == 20
    metrics = controller.historyAnalytics
    assert metrics["attempts"] == 20
    assert metrics["accuracyPercent"] == 50  # skipped answers do not enter this denominator
    assert metrics["skipped"] == 20
    assert metrics["practiceTimeMs"] == 20000
    assert metrics["averageResponseTimeMs"] == 5000  # cloud divides by answered, not graded
    assert len(metrics["trends"]) == 20

    controller.setAnalyticsWindow(5)
    metrics = controller.historyAnalytics
    assert metrics["attempts"] == 5
    assert metrics["correct"] == 5
    assert len(metrics["trends"]) == 5
    controller.setAnalyticsWindow(7)
    assert controller.analyticsWindow == 5
    controller._countdown_timer.stop()


def test_offline_qt_assessment_survives_restart_and_history_review(qapp, tmp_path):
    """Run the native QML assessment against a disposable SQLite database offline."""
    import hashlib
    import json
    import time
    from uuid import uuid4

    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtGui import QFont, QFontDatabase
    from PySide6.QtQuick import QQuickWindow
    from PySide6.QtTest import QTest

    from app.data.repo import Repository

    database = tmp_path / "offline-qt-assessment.db"
    for font_file in ("segoeui.ttf", "segoeuib.ttf", "segoeuisb.ttf", "arial.ttf", "arialbd.ttf"):
        font_path = Path("C:/Windows/Fonts") / font_file
        if font_path.exists():
            QFontDatabase.addApplicationFont(str(font_path))
    qapp.setFont(QFont("Segoe UI", 11))
    credentials = CredentialStore(tmp_path / "offline-credentials.json")
    config = AppConfig(database_path=database, api_base_url=None)
    repo = Repository(database)
    account_id, cloud_profile_id, link_id = (str(uuid4()) for _ in range(3))
    profile = Profile("offline-student", "Offline Student", cloud_account_id=account_id,
                      cloud_profile_id=cloud_profile_id, ownership_state="owned", link_state="linked")
    repo.create_profile(profile)
    repo.apply_profile_link(profile.id, {
        "status": "linked", "link_id": link_id, "student_account_id": account_id,
        "study_profile_id": cloud_profile_id, "local_profile_id": profile.id,
        "account_display_name": "Offline Account", "study_profile_name": "Offline Student",
    })
    qset = QuestionSet(
        "offline-memory-mcq", 1, "Memory Check", "Biology", "Cells", MarkingScheme(),
        (
            Question("q1", 1, "Cells", 1, "Which cell structure stores DNA?",
                     (Option("A", "Nucleus"), Option("B", "Ribosome"),
                      Option("C", "Cell membrane"), Option("D", "Cytoplasm")), "A"),
            Question("q2", 2, "Cells", 1, "Which structure makes proteins?",
                     (Option("A", "Mitochondrion"), Option("B", "Ribosome"),
                      Option("C", "Nucleus"), Option("D", "Vacuole")), "B"),
            Question("q3", 3, "Cells", 1, "Which structure controls entry?",
                     (Option("A", "Membrane"), Option("B", "Cell wall"),
                      Option("C", "Ribosome"), Option("D", "Nucleus")), "A"),
        ),
    )
    local_hash = hashlib.sha256(b"offline-test").hexdigest()
    repo.import_question_set(qset, content_hash=f"sha256:{local_hash}", is_active=True)
    repo.cache_profile_library(profile.id, link_id, [{
        "set_id": qset.id, "version": qset.version, "title": qset.title,
        "subject": qset.subject, "chapter": qset.chapter,
        "question_count": len(qset.questions), "size_bytes": 1,
        "sha256": local_hash, "published_at": "2026-11-12T00:00:00Z",
    }])
    repo.close()

    def launch():
        app_ctrl = AppController(database, config, credentials)
        offline_repository = Repository(database)
        offline_repository.set_setting("connectivity_cloud", json.dumps({"state": "Offline"}))
        offline_repository.set_setting("connectivity_sync", "Offline")
        app_ctrl.startup_session.repository = offline_repository
        app_ctrl.startup_session.complete = True
        app_ctrl._initialize_runtime()
        app_ctrl._poll_timer.stop()  # no connectivity probes or background network activity
        profile_ctrl = ProfileController(app_ctrl)
        library_ctrl = LibraryController(app_ctrl)
        assessment_ctrl = AssessmentController(app_ctrl)
        settings_ctrl = SettingsController(app_ctrl)
        quick_add_ctrl = QuickAddController(app_ctrl)
        engine = QQmlApplicationEngine()
        qml = Path("app/ui_qt/qml").resolve()
        engine.addImportPath(str(qml))
        for name, controller in (
            ("appController", app_ctrl), ("profileController", profile_ctrl),
            ("libraryController", library_ctrl), ("assessmentController", assessment_ctrl),
            ("settingsController", settings_ctrl), ("quickAddController", quick_add_ctrl),
        ):
            engine.rootContext().setContextProperty(name, controller)
        engine.load(QUrl.fromLocalFile(str(qml / "App.qml")))
        assert engine.rootObjects()
        profile_ctrl.selectProfile(0)
        library_ctrl._selected_pack_id = qset.id
        library_ctrl._selected_pack_version = qset.version
        qapp.processEvents()
        return app_ctrl, library_ctrl, assessment_ctrl, settings_ctrl, engine

    app_ctrl, library_ctrl, assessment_ctrl, settings_ctrl, engine = launch()
    assert app_ctrl.config.api_base_url is None
    assessment_ctrl.startTest("practice", 0, 3, "", "", False)
    time.sleep(1.1)  # ensure persisted practice duration has visible sub-minute evidence
    assessment_ctrl.selectAnswer("A")
    assessment_ctrl.setConfidence("sure")
    assessment_ctrl.selectAnswer("A")
    assessment_ctrl.setConfidence("guessing")
    assessment_ctrl.nextQuestion()  # leave the last response skipped
    assessment_ctrl.confirmSubmit()
    assert app_ctrl.screen == "result"
    assert assessment_ctrl.score == 3
    assert assessment_ctrl.scoreMax == 12
    assert assessment_ctrl.scorePercent == 25
    assert (assessment_ctrl.correctCount, assessment_ctrl.wrongCount, assessment_ctrl.skippedCount) == (1, 1, 1)
    first = assessment_ctrl.historyAnalytics
    assert first["attempts"] == 1
    assert first["correct"] == 1 and first["wrong"] == 1 and first["skipped"] == 1
    assert first["accuracyPercent"] == 50
    assert first["practiceTimeMs"] > 0
    assert first["averageResponseTimeMs"] > 0
    attempt_id = assessment_ctrl.historyList[0]["attemptId"]

    capture_dir = Path(__file__).resolve().parents[1] / "artifacts" / "offline-final-verification"
    capture_dir.mkdir(parents=True, exist_ok=True)
    review_window = engine.rootObjects()[0]
    app_ctrl.navigate("history")
    qapp.processEvents()
    QTest.qWait(100)
    QTest.mouseClick(review_window, Qt.MouseButton.LeftButton, pos=QPoint(400, 88))
    qapp.processEvents()
    assert app_ctrl.screen == "review"
    assert len(assessment_ctrl.reviewItems) == 3
    assert assessment_ctrl.reviewItems[2]["isSkipped"] is True
    QTest.qWait(60)
    assert review_window.grabWindow().save(str(capture_dir / "assessment-review-800x480.png"))
    assessment_ctrl.closeReview()
    assert app_ctrl.screen == "history"
    qapp.processEvents()
    QTest.qWait(60)
    assert review_window.grabWindow().save(str(capture_dir / "history-800x480.png"))
    app_ctrl.navigate("result")
    qapp.processEvents()
    QTest.qWait(60)
    assert review_window.grabWindow().save(str(capture_dir / "assessment-result-800x480.png"))
    app_ctrl.navigate("progress")
    qapp.processEvents()
    QTest.qWait(60)
    window = review_window
    assert isinstance(window, QQuickWindow)
    assert (window.width(), window.height()) == (800, 480)
    screenshot = window.grabWindow()
    assert not screenshot.isNull()
    assert screenshot.width() == 800 and screenshot.height() == 480
    assert screenshot.save(str(capture_dir / "progress-analytics-800x480.png"))
    analytics_flickable = window.findChild(QObject, "progressAnalyticsFlickable")
    average_answer_text = window.findChild(QObject, "averageAnswerTimeText")
    assert analytics_flickable is not None and average_answer_text is not None
    assert "Average answer time:" in average_answer_text.property("text")
    max_scroll = max(
        0, float(analytics_flickable.property("contentHeight"))
        - float(analytics_flickable.property("height")),
    )
    analytics_flickable.setProperty("contentY", max_scroll)
    qapp.processEvents()
    QTest.qWait(60)
    assert window.grabWindow().save(str(capture_dir / "progress-analytics-details-800x480.png"))
    analytics_flickable.setProperty("contentY", 0)

    # Model a cloud-delivered eligible recovery pack already installed in SQLite.
    recovery_pack = QuestionSet(
        "recovery-pi-offline-cells", 1, "Recovery check: Cells", "Biology", "Cells",
        MarkingScheme(), (
            Question("recovery-q1", 1, "Cells", 1, "Which organelle stores DNA?",
                     (Option("A", "Nucleus"), Option("B", "Ribosome"),
                      Option("C", "Cell membrane"), Option("D", "Cytoplasm")), "A"),
        ),
    )
    app_ctrl.repository.import_question_set(
        recovery_pack, content_hash="sha256:recovery-offline", is_active=True
    )
    recovery_hash = hashlib.sha256(b"recovery-offline").hexdigest()
    eligible_packs = [
        {"set_id": qset.id, "version": qset.version, "title": qset.title,
         "subject": qset.subject, "chapter": qset.chapter, "question_count": len(qset.questions),
         "size_bytes": 1, "sha256": local_hash, "published_at": "2026-11-12T00:00:00Z"},
        {"set_id": recovery_pack.id, "version": recovery_pack.version, "title": recovery_pack.title,
         "subject": recovery_pack.subject, "chapter": recovery_pack.chapter, "question_count": 1,
         "size_bytes": 1, "sha256": recovery_hash, "published_at": "2026-11-12T00:00:00Z"},
    ]
    app_ctrl.repository.cache_profile_library(profile.id, link_id, eligible_packs)
    app_ctrl.ui_controller.refresh_catalog()
    assert recovery_pack.id in {item["id"] for item in settings_ctrl.installedPacks}
    app_ctrl.navigate("content")
    qapp.processEvents()
    QTest.qWait(100)
    assert window.grabWindow().save(str(capture_dir / "recovery-practice-screen-800x480.png"))
    QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(400, 266))
    qapp.processEvents()
    assert app_ctrl.screen == "test_setup"
    assert library_ctrl._selected_pack_id == recovery_pack.id
    assessment_ctrl.startTest("practice", 0, 1, "", "", False)
    assessment_ctrl.selectAnswer("A")
    assessment_ctrl.setConfidence("sure")
    assessment_ctrl.confirmSubmit()
    assert app_ctrl.screen == "result"
    assert assessment_ctrl.historyAnalytics["attempts"] == 2
    assert assessment_ctrl.historyAnalytics["accuracyPercent"] == 67
    recovery_attempts = [item for item in assessment_ctrl.historyList
                         if item["title"] == "Recovery check: Cells"]
    assert recovery_attempts, assessment_ctrl.historyList
    recovery_attempt = recovery_attempts[0]
    recovery_attempt_id = recovery_attempt["attemptId"]
    app_ctrl.navigate("progress")
    qapp.processEvents()
    QTest.qWait(60)
    assert window.grabWindow().save(str(capture_dir / "progress-after-recovery-practice-800x480.png"))
    app_ctrl.navigate("sync")
    qapp.processEvents()
    QTest.qWait(60)
    assert settings_ctrl.syncStatusSummary
    assert settings_ctrl.syncDetail
    sync_root = engine.rootObjects()[0]
    assert sync_root.findChild(QObject, "syncStatusSummaryText").property("text") == settings_ctrl.syncStatusSummary
    assert sync_root.findChild(QObject, "syncDetailText").property("text") == settings_ctrl.syncDetail
    assert window.grabWindow().save(str(capture_dir / "sync-status-800x480.png"))
    app_ctrl.repository.set_setting("last_full_sync", json.dumps({
        "result": "Partially synced",
        "stages": {"history": "ConnectionError", "attempt_uploads": {"failed": 2}},
    }))
    settings_ctrl.syncChanged.emit()
    assert "History download needs a retry" in settings_ctrl.syncDetail
    assert "2 assessment upload(s) need a retry" in settings_ctrl.syncDetail
    qapp.processEvents()
    QTest.qWait(60)
    assert window.grabWindow().save(str(capture_dir / "sync-status-error-800x480.png"))
    engine.deleteLater()
    qapp.sendPostedEvents()
    qapp.processEvents()
    app_ctrl.close()

    app_ctrl, library_ctrl, assessment_ctrl, settings_ctrl, engine = launch()
    persisted = assessment_ctrl.historyAnalytics
    assert persisted["attempts"] == 2
    assert (persisted["correct"], persisted["wrong"], persisted["skipped"]) == (2, 1, 1)
    assert persisted["accuracyPercent"] == 67
    assert {item["attemptId"] for item in assessment_ctrl.historyList} == {
        attempt_id, recovery_attempt_id,
    }
    app_ctrl.navigate("progress")
    qapp.processEvents()
    QTest.qWait(60)
    restarted_screenshot = engine.rootObjects()[0].grabWindow()
    assert not restarted_screenshot.isNull()
    assert restarted_screenshot.save(str(capture_dir / "progress-after-restart-800x480.png"))
    # Cache a cloud-completed web assessment after restart and open it through
    # the real History row and existing Review screen while the app stays offline.
    web_attempt_id = str(uuid4())
    app_ctrl.repository.cache_completed_results(profile.id, link_id, [{
        "attempt_id": web_attempt_id,
        "study_profile_id": cloud_profile_id,
        "source": "web",
        "status": "completed",
        "set_id": "offline-memory-mcq",
        "version": 1,
        "title": "Web Memory Check",
        "subject": "Biology",
        "started_at": "2026-11-14T10:00:00Z",
        "completed_at": "2026-11-14T10:02:00Z",
        "result": {"score": 4, "maximum_score": 12, "correct": 1, "wrong": 1,
                   "skipped": 1, "duration_ms": 120000, "response_time_ms": 5000,
                   "answered": 2, "confidence": {"sure": {"correct": 1, "wrong": 0}}},
        "review": [{"question_id": "web-q1", "question_text": "Which organelle stores DNA?",
                    "options": [{"key": "A", "text": "Nucleus"}, {"key": "B", "text": "Ribosome"}],
                    "correct_key": "A", "selected_key": "B", "confidence": "guessing",
                    "is_correct": False, "explanation": "DNA is stored in the nucleus.",
                    "marked_review": False, "response_time_ms": 5000}],
        "review_available": True,
    }])
    assessment_ctrl.historyChanged.emit()
    assert assessment_ctrl.historyList[0]["attemptId"] == web_attempt_id
    app_ctrl.navigate("history")
    qapp.processEvents()
    QTest.qWait(60)
    QTest.mouseClick(engine.rootObjects()[0], Qt.MouseButton.LeftButton, pos=QPoint(400, 88))
    qapp.processEvents()
    assert app_ctrl.screen == "review"
    assert assessment_ctrl.reviewItems[0]["question"] == "Which organelle stores DNA?"
    assert assessment_ctrl.reviewItems[0]["isCorrect"] is False
    assert assessment_ctrl.reviewItems[0]["explanation"] == "DNA is stored in the nucleus."
    assert engine.rootObjects()[0].grabWindow().save(
        str(capture_dir / "web-attempt-review-800x480.png")
    )
    engine.deleteLater()
    qapp.sendPostedEvents()
    qapp.processEvents()
    app_ctrl.close()



def test_practice_filters_expose_count_presets_and_allow_empty_matches(qapp, mock_repo):
    app = Mock()
    app.repository = mock_repo
    controller = LibraryController(app)
    controller._selected_pack_id = "bio-pack-01"
    controller._selected_pack_version = 1

    assert controller.practiceQuestionCount("All topics", "Any difficulty") == 1
    assert controller.practiceCountPresets("All topics", "Any difficulty") == ["All questions", "Custom"]
    assert controller.practiceQuestionCount("Fractions", "Standard") == 0
    assert controller.practiceCountPresets("Fractions", "Standard") == []
