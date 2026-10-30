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
            "result": {"score": 4, "maximum_score": 8}}])
    app_ctrl._on_tick()
    qapp.processEvents()
    assert changed
    assert assessment.historyList[0]["title"] == "Browser completion"
    assert assessment.historyList[0]["synced"] is True
    assert repo.get_attempt(result_id) is None
    window = engine.rootObjects()[0]
    assert isinstance(window, QQuickWindow)
    image = window.grabWindow()
    assert not image.isNull()
    assert image.save(str(tmp_path / "history-down-sync.png"))
    assert next(item for item in settings.diagnosticItems if item["name"] == "Last Full Sync")["status"] == "Up to date"
    app_ctrl.navigate("diagnostics")
    qapp.processEvents()
    assert window.grabWindow().save(str(tmp_path / "sync-diagnostics.png"))
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
