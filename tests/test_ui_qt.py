"""Automated smoke and functional regression tests for the PySide6/QML UI."""

import json
import os
from concurrent.futures import Future
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest
from packaging.version import Version

# Ensure headless offscreen platform for CI/automated testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QSG_RENDER_LOOP"] = "basic"
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine

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
from app.ui_qt.main import close_qml


def visual_item(parent, name):
    if parent.objectName() == name:
        return parent
    for child in parent.childItems():
        if item := visual_item(child, name):
            return item
    return None


@pytest.fixture
def mock_repo(tmp_path):
    repo = Mock()
    repo.schema_version = 8
    repo.get_or_create_device_id.return_value = "rpi-test-01"
    repo.quick_check.return_value = Mock(ok=True)
    repo.get_student_account_context.return_value = {
        "cloud_account_id": "acc-01",
        "display_name": "Aksh",
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
    repo.completed_attempt_times.return_value = ()
    repo.completed_results.return_value = []
    repo.save_response.side_effect = lambda resp, *args, **kwargs: resp
    repo.create_attempt.return_value = Mock(id="att-01", profile_id="prof-01", set_id="bio-pack-01", set_version=1)
    return repo


@pytest.fixture
def qml_app(tmp_path, mock_repo, qt_owner):
    db_path = tmp_path / "test.db"
    db_path.touch()

    config = AppConfig(database_path=db_path)
    creds = CredentialStore(tmp_path / "creds.json")

    engine = QQmlApplicationEngine(parent=qt_owner)
    qml_dir = Path("app/ui_qt/qml").resolve()
    engine.addImportPath(str(qml_dir))

    app_ctrl = AppController(db_path, config, creds, parent=qt_owner)
    # inject mock repo to avoid needing migrations during offscreen unit test
    app_ctrl.startup_session.repository = mock_repo
    app_ctrl.startup_session.complete = True
    app_ctrl._initialize_runtime()

    prof_ctrl = ProfileController(app_ctrl, parent=app_ctrl)
    lib_ctrl = LibraryController(app_ctrl, parent=app_ctrl)
    assess_ctrl = AssessmentController(app_ctrl, parent=app_ctrl)
    settings_ctrl = SettingsController(app_ctrl, parent=app_ctrl)
    quick_add_ctrl = QuickAddController(app_ctrl, parent=app_ctrl)

    ctx = engine.rootContext()
    ctx.setContextProperty("appController", app_ctrl)
    ctx.setContextProperty("profileController", prof_ctrl)
    ctx.setContextProperty("libraryController", lib_ctrl)
    ctx.setContextProperty("assessmentController", assess_ctrl)
    ctx.setContextProperty("settingsController", settings_ctrl)
    ctx.setContextProperty("quickAddController", quick_add_ctrl)

    app_qml = qml_dir / "App.qml"
    engine.load(QUrl.fromLocalFile(str(app_qml)))

    assert engine.rootObjects(), "Failed to load App.qml root object"
    return engine, app_ctrl, lib_ctrl


def test_qml_app_loads(qapp, tmp_path, qml_app):
    """Verify that App.qml and all components load cleanly into QQmlApplicationEngine."""
    engine, app_ctrl, lib_ctrl = qml_app
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


def test_native_touch_uses_tap_position_and_scrolls_without_clicking(qapp, qml_app, monkeypatch):
    from PySide6.QtCore import QPoint
    from PySide6.QtTest import QSignalSpy, QTest

    engine, app_ctrl, _ = qml_app
    window = engine.rootObjects()[0]
    app_ctrl.navigate("home")
    qapp.processEvents()

    def center(item):
        return item.mapToScene(QPoint(int(item.width() / 2), int(item.height() / 2))).toPoint()

    def nav_button(tab):
        label = visual_item(window.contentItem(), f"navLabel-{tab}")
        return label.parentItem().parentItem().parentItem()

    # Place the mouse over History, then send a direct touch to Settings.
    history_button = nav_button("history")
    settings_button = nav_button("settings")
    history_clicks = QSignalSpy(history_button.clicked)
    settings_clicks = QSignalSpy(settings_button.clicked)
    QTest.mouseMove(window, center(history_button))
    assert history_button.property("hovered")
    touch = QTest.createTouchDevice()
    settings_pos = center(settings_button)
    QTest.touchEvent(window, touch).press(0, settings_pos).commit()
    QTest.touchEvent(window, touch).release(0, settings_pos).commit()
    assert app_ctrl.screen == "settings"
    assert settings_clicks.count() == 1
    assert history_clicks.count() == 0

    # A scroll starting on an interactive history card must not activate it.
    rows = tuple(
        HistoryItem("Practice", "Biology", 1, 1, None, SyncStatus.PENDING, attempt_id=f"row-{i}")
        for i in range(12)
    )
    monkeypatch.setattr(type(app_ctrl.ui_controller), "history_items", property(lambda _: rows))
    app_ctrl.navigate("history")
    qapp.processEvents()
    card = visual_item(window.contentItem(), "history-row-row-2")
    list_view = card.parentItem().parentItem().parentItem()
    clicks = QSignalSpy(card.clicked)
    start = center(card)
    QTest.touchEvent(window, touch).press(0, start).commit()
    QTest.touchEvent(window, touch).release(0, start).commit()
    assert clicks.count() == 1

    QTest.touchEvent(window, touch).press(0, start).commit()
    for dy in (30, 70, 110):
        QTest.touchEvent(window, touch).move(0, start - QPoint(0, dy)).commit()
        # Give Qt Quick a frame to deliver each compressed touch update.
        QTest.qWait(25)
    QTest.touchEvent(window, touch).release(0, start - QPoint(0, 110)).commit()
    assert list_view.property("contentY") > 0
    assert clicks.count() == 1
    assert app_ctrl.screen == "history"


def test_qt_entry_point_hides_cursor_until_qml_closes(qapp, tmp_path, monkeypatch):
    from PySide6.QtCore import Qt

    from app.ui_qt import main as qt_main

    monkeypatch.setattr(qt_main, "QGuiApplication", lambda _: qapp)
    monkeypatch.setattr(qt_main, "configure_logging", Mock())

    def close_with_cursor_check(engine, controller):
        try:
            assert engine.rootObjects()
            assert qapp.overrideCursor().shape() == Qt.CursorShape.BlankCursor
        finally:
            close_qml(engine, controller)

    monkeypatch.setattr(qt_main, "close_qml", close_with_cursor_check)
    config = AppConfig(
        database_path=tmp_path / "startup.db",
        credential_path=tmp_path / "credentials.json",
        log_directory=tmp_path / "logs",
    )
    previous_cursor = qapp.overrideCursor()
    assert qt_main.run(config.database_path, config=config, smoke_test=True) == 0
    assert qapp.overrideCursor() == previous_cursor


def test_navigation_and_controller_properties(qapp, tmp_path, mock_repo, qt_owner):
    """Verify routing and property transitions in controllers."""
    db_path = tmp_path / "test.db"
    db_path.touch()

    config = AppConfig(database_path=db_path)
    creds = CredentialStore(tmp_path / "creds.json")

    app_ctrl = AppController(db_path, config, creds, parent=qt_owner)
    app_ctrl.startup_session.repository = mock_repo
    app_ctrl.startup_session.complete = True
    app_ctrl._initialize_runtime()

    assert app_ctrl.screen in {"profile_picker", "home", "pairing"}

    # Test navigation
    ProfileController(app_ctrl, parent=app_ctrl).selectProfile(0)
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


def test_external_browser_history_commit_refreshes_rendered_qt_model(qapp, tmp_path, qt_owner):
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
    app_ctrl = AppController(path, config, CredentialStore(tmp_path / "creds"), parent=qt_owner)
    app_ctrl.startup_session.repository = repo
    app_ctrl.startup_session.complete = True
    app_ctrl._initialize_runtime()
    prof = ProfileController(app_ctrl, parent=app_ctrl)
    library = LibraryController(app_ctrl, parent=app_ctrl)
    assessment = AssessmentController(app_ctrl, parent=app_ctrl)
    settings = SettingsController(app_ctrl, parent=app_ctrl)
    engine = QQmlApplicationEngine(parent=qt_owner)
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
    close_qml(engine, app_ctrl)


def test_cloud_echo_of_local_attempt_is_counted_once(tmp_path, qt_owner):
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
    repo.cache_student_account_context(account, "Student")
    app_ctrl = AppController(path, AppConfig(database_path=path),
        CredentialStore(tmp_path / "dedup-creds.json"), parent=qt_owner)
    app_ctrl.startup_session.repository = repo
    app_ctrl.startup_session.complete = True
    app_ctrl._initialize_runtime()
    assessment = AssessmentController(app_ctrl, parent=app_ctrl)

    assert len(assessment.historyList) == 1
    assert assessment.historyList[0]["source"] == "device"
    assert assessment.historyAnalytics["attempts"] == 1
    assert assessment.historyAnalytics["correct"] == 1
    assert assessment.historyAnalytics["confidence"]["sure"]["correct"] == 1

    app_ctrl.close()


def test_profile_controller_listing_and_selection(qapp, tmp_path, mock_repo, qt_owner):
    from app.auth.credentials import DeviceCredential

    db_path = tmp_path / "test.db"
    db_path.touch()

    config = AppConfig(database_path=db_path)
    creds = CredentialStore(tmp_path / "creds.json")

    app_ctrl = AppController(db_path, config, creds, parent=qt_owner)
    app_ctrl.startup_session.repository = mock_repo
    app_ctrl.startup_session.complete = True
    app_ctrl._initialize_runtime()

    prof_ctrl = ProfileController(app_ctrl, parent=app_ctrl)
    assert prof_ctrl.profileCount >= 1
    assert prof_ctrl.canAddProfile is False
    prof_ctrl.createProfile("Should not be created", "Primary 5")
    assert "Connect your account" in app_ctrl.message
    app_ctrl.navigate("create_profile")
    assert app_ctrl.screen == "pairing"

    creds.save(DeviceCredential("rpi-test-01", "device_test.secret"))
    assert prof_ctrl.canAddProfile is True
    app_ctrl.navigate("create_profile")
    assert app_ctrl.screen == "create_profile"
    app_ctrl.navigate("wifi")
    creds.clear()
    app_ctrl.goBack()
    assert app_ctrl.screen == "pairing"
    assert not prof_ctrl.canAddProfile

    prof_ctrl.selectProfile(0)
    assert app_ctrl.screen == "home"

    app_ctrl.close()


def test_library_and_assessment_properties(qapp, tmp_path, mock_repo, qt_owner):
    db_path = tmp_path / "test.db"
    db_path.touch()

    config = AppConfig(database_path=db_path)
    creds = CredentialStore(tmp_path / "creds.json")

    app_ctrl = AppController(db_path, config, creds, parent=qt_owner)
    app_ctrl.startup_session.repository = mock_repo
    app_ctrl.startup_session.complete = True
    app_ctrl._initialize_runtime()

    lib_ctrl = LibraryController(app_ctrl, parent=app_ctrl)
    assert lib_ctrl.subjects == ["Biology"]
    assert lib_ctrl.chapters == []
    lib_ctrl.selectInstalledSubject("Biology")
    assert lib_ctrl.chapters == ["Cells"]

    assess_ctrl = AssessmentController(app_ctrl, parent=app_ctrl)
    assert assess_ctrl.questionIndex == 1
    assert assess_ctrl.answeredCount == 0

    app_ctrl.close()


def test_assessment_flow_full(qapp, tmp_path, mock_repo, qt_owner):
    """Test full assessment interaction: start, select answer, confidence, submit, and review."""
    db_path = tmp_path / "test.db"
    db_path.touch()

    config = AppConfig(database_path=db_path)
    creds = CredentialStore(tmp_path / "creds.json")

    app_ctrl = AppController(db_path, config, creds, parent=qt_owner)
    app_ctrl.startup_session.repository = mock_repo
    app_ctrl.startup_session.complete = True
    app_ctrl._initialize_runtime()

    assess_ctrl = AssessmentController(app_ctrl, parent=app_ctrl)

    # Mock application methods for active assessment
    mock_app = Mock()
    app_ctrl.ui_controller.application = mock_app
    mock_question = mock_repo.get_question_set("bio-pack-01", 1).questions[0]
    mock_app.current_question.return_value = mock_question
    mock_app.current_response.return_value = Mock(selected_key="A", marked_review=False)

    LibraryController(app_ctrl, parent=app_ctrl).selectPack("bio-pack-01", 1)
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


def test_settings_controller_operations(qapp, tmp_path, mock_repo, qt_owner):
    """Test SettingsController Wi-Fi, Sync, Update, and Diagnostics triggers."""
    db_path = tmp_path / "test.db"
    db_path.touch()

    config = AppConfig(database_path=db_path)
    creds = CredentialStore(tmp_path / "creds.json")

    app_ctrl = AppController(db_path, config, creds, parent=qt_owner)
    app_ctrl.startup_session.repository = mock_repo
    app_ctrl.startup_session.complete = True
    app_ctrl._initialize_runtime()

    settings_ctrl = SettingsController(app_ctrl, parent=app_ctrl)
    assert len(settings_ctrl.availableNetworks) >= 1
    assert settings_ctrl.overallHealth == app_ctrl.networkLabel
    assert settings_ctrl.storageUsedGb > 0
    assert settings_ctrl.storageTotalGb > 0

    # Verify dispatch without scanning Wi-Fi or contacting the cloud from a Qt test.
    app_ctrl.device.start = Mock()
    settings_ctrl.scanWifi()
    settings_ctrl.startSync()
    settings_ctrl.checkUpdate()
    settings_ctrl.runDiagnostics()
    assert app_ctrl.device.start.call_args_list == [
        call("wifi_scan"), call("sync"), call("update_check"), call("diagnostics"),
    ]
    assert settings_ctrl._update_timer.isActive() and settings_ctrl._sync_countdown.isActive()

    app_ctrl.close()
    assert not settings_ctrl._update_timer.isActive() and not settings_ctrl._sync_countdown.isActive()


@pytest.fixture
def update_controller(qapp, tmp_path, mock_repo, monkeypatch, qt_owner):
    active = SimpleNamespace(version=None)
    monkeypatch.setattr(
        "app.ui_qt.controllers.settings_controller.active_release_version", lambda: active.version
    )
    controllers = []

    def start(running_version):
        db_path = tmp_path / "update-controller.db"
        db_path.touch()
        config = AppConfig(
            database_path=db_path, application_version=running_version,
            update_root=tmp_path, update_inbox=tmp_path / "inbox",
            update_platform="linux", update_architecture="aarch64",
        )
        app = AppController(db_path, config, CredentialStore(tmp_path / "creds.json"), parent=qt_owner)
        app.startup_session.repository = mock_repo
        app.startup_session.complete = True
        app._initialize_runtime()
        app._poll_timer.stop()
        controllers.append(app)
        return app, SettingsController(app, parent=app)

    yield start, active
    for app in controllers:
        app.close()


def _available_release(version, *, architecture="aarch64"):
    return SimpleNamespace(manifest=SimpleNamespace(
        version=Version(version),
        data={
            "compatibility": {"platform": "linux", "architecture": architecture},
            "release": {"required_db_schema": 8, "min_supported_version": "0.1.0",
                        "notes": "Stability improvements"},
        },
    ))


def _write_update_status(tmp_path, state, version, **extra):
    pending = tmp_path / "status.tmp"
    pending.write_text(json.dumps({"state": state, "version": version, "detail": "", **extra}), encoding="utf-8")
    pending.replace(tmp_path / "status.json")


def test_automatic_update_notice_waits_for_idle_and_remembers_later(update_controller, qapp, mock_repo, monkeypatch,
                                                                  qt_owner, tmp_path):
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QFont, QFontDatabase
    from PySide6.QtTest import QTest

    from app.auth.credentials import DeviceCredential
    from app.connectivity import CLOUD_KEY

    start, active = update_controller
    if os.name == "nt":
        fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        for font in ("arial.ttf", "arialbd.ttf", "georgia.ttf", "georgiab.ttf", "segoeui.ttf"):
            QFontDatabase.addApplicationFont(str(fonts / font))
        qapp.setFont(QFont("Segoe UI", 11))
    active.version = Version("0.1.7")
    clock = SimpleNamespace(now=100.0)
    monkeypatch.setattr("app.ui_qt.controllers.settings_controller.monotonic", lambda: clock.now)
    monkeypatch.setattr("app.ui_qt.controllers.settings_controller.time", lambda: 1_700_000_000 + clock.now)
    stored = {CLOUD_KEY: '{"state":"Offline"}'}
    original_setting = mock_repo.get_setting.side_effect
    mock_repo.get_setting.side_effect = lambda key: stored[key] if key in stored else original_setting(key)
    mock_repo.set_setting.side_effect = stored.__setitem__
    monkeypatch.setenv("ASSESS_API_URL", "https://cloud.test")
    app, settings = start("0.1.7")
    settings._update_timer.stop()
    app.credentials.save(DeviceCredential("test-pi", "device-token"))

    def begin(operation, **kwargs):
        assert operation == "update_check"
        app.device.operation = operation
        app.device.update_check_automatic = kwargs.get("automatic", False)
        app.device.failure = None
        app.device.future = Future()

    app.device.start = Mock(side_effect=begin)
    engine = QQmlApplicationEngine(parent=qt_owner)
    qml_dir = Path("app/ui_qt/qml").resolve()
    engine.addImportPath(str(qml_dir))
    for name, controller in (
        ("appController", app), ("profileController", ProfileController(app, parent=app)),
        ("libraryController", LibraryController(app, parent=app)),
        ("assessmentController", AssessmentController(app, parent=app)),
        ("settingsController", settings), ("quickAddController", QuickAddController(app, parent=app)),
    ):
        engine.rootContext().setContextProperty(name, controller)
    engine.load(QUrl.fromLocalFile(str(qml_dir / "App.qml")))
    try:
        window, = engine.rootObjects()
        popup = window.findChild(QObject, "softwareUpdateNotice")
        loader = window.findChild(QObject, "screenLoader")

        def reminder_visible(item):
            if item.objectName() == "homeSoftwareUpdateReminder":
                return item.isVisible() and item.width() > 0
            return any(reminder_visible(child) for child in item.childItems())

        app.navigate("home")
        qapp.processEvents()
        settings._pollUpdateState()
        app.device.start.assert_not_called()
        assert not popup.property("visible")
        assert not reminder_visible(loader)

        stored[CLOUD_KEY] = '{"state":"Online"}'
        clock.now += 5
        settings._pollUpdateState()
        app.device.start.assert_called_once_with("update_check", automatic=True)
        app.navigate("result")
        app.device.future.set_result((app.device.generation, _available_release("0.1.8")))
        app._on_tick()
        assert settings.updateReminderVersion == "0.1.8"
        assert not popup.property("visible")
        assert app.message == ""

        app.navigate("home")
        qapp.processEvents()
        assert popup.property("visible")
        assert reminder_visible(loader)
        QTest.qWait(150)
        assert window.grabWindow().save(str(tmp_path / "software-update-notice-800x480.png"))
        later = popup.findChild(QObject, "softwareUpdateLater")
        position = later.mapToScene(QPointF(later.width() / 2, later.height() / 2)).toPoint()
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=position)
        assert not popup.property("visible")
        assert reminder_visible(loader)
        assert settings.updateNoticeVersion == ""
        QTest.qWait(150)
        assert window.grabWindow().save(str(tmp_path / "software-update-reminder-800x480.png"))

        clock.now += 15 * 60
        settings._pollUpdateState()
        app.device.start.assert_called_once_with("update_check", automatic=True)

        restarted, restored = start("0.1.7")
        restored._update_timer.stop()
        restarted.navigate("home")
        restarted.device.start = Mock()
        assert restarted.isOnline
        restored._pollUpdateState()
        restarted.device.start.assert_not_called()
        assert restored.updateReminderVersion == "0.1.8"
        assert restored.updateNoticeVersion == ""
        assert restarted.device.available_update is None

        clock.now += 24 * 60 * 60 - 15 * 60
        settings._pollUpdateState()
        app.device.future.set_result((app.device.generation, _available_release("0.1.9")))
        app._on_tick()
        assert popup.property("visible") and settings.updateNoticeVersion == "0.1.9"
        view = popup.findChild(QObject, "softwareUpdateView")
        position = view.mapToScene(QPointF(view.width() / 2, view.height() / 2)).toPoint()
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=position)
        assert app.screen == "software_update" and settings.updateNoticeVersion == ""
        assert app.device.start.call_args_list == [call("update_check", automatic=True)] * 2

        clock.now += 24 * 60 * 60
        settings._pollUpdateState()
        app.device.future.set_exception(RuntimeError("Update service unavailable"))
        app._on_tick()
        clock.now += 15 * 60
        settings._pollUpdateState()
        assert app.device.start.call_args_list == [call("update_check", automatic=True)] * 3

        settings.checkUpdate()
        app.device.start.assert_called_with("update_check")
        app.device.future.set_result((app.device.generation, _available_release("0.1.9")))
        app._on_tick()

        active.version = Version("0.1.9")
        settings.refreshUpdateState()
        assert settings.updateReminderVersion == ""
    finally:
        close_qml(engine, app)


def test_update_controller_binds_signed_release_and_actions(update_controller):
    start, active = update_controller
    active.version = Version("0.1.0")
    app, settings = start("0.1.0")
    release = _available_release("0.1.1")
    app.device.available_update = release
    app.device.start = Mock()
    settings.refreshUpdateState()

    assert settings.appVersion == "0.1.0"
    assert settings.hasUpdate
    assert settings.updateCompatible
    assert settings.availableVersion == "0.1.1"
    assert settings.updateNotes == "Stability improvements"
    settings.checkUpdate()
    settings.downloadUpdate()
    assert [call.args[0] for call in app.device.start.call_args_list] == ["update_check", "update_download"]
    assert app.device.start.call_args.kwargs["update"] is release


@pytest.mark.parametrize("latest", [None, "0.1.0", "0.1.1"])
def test_update_controller_hides_obsolete_release(update_controller, latest):
    start, active = update_controller
    active.version = Version("0.1.1")
    app, settings = start("0.1.1")
    if latest:
        app.device.available_update = _available_release(latest, architecture="wrong")
    settings.refreshUpdateState()

    assert settings.updateStatus == "Software is up to date"
    assert not settings.hasUpdate
    assert settings.updateVersion == settings.availableVersion == settings.updateNotes == ""
    assert not settings.updateCompatible
    app.device.start = Mock()
    settings.downloadUpdate()
    app.device.start.assert_not_called()


def test_update_controller_preserves_running_version_until_restart(update_controller, tmp_path):
    start, active = update_controller
    active.version = Version("0.1.0")
    app, settings = start("0.1.0")
    app.device.available_update = _available_release("0.1.1")
    _write_update_status(tmp_path, "failed", "0.1.1")
    settings.refreshUpdateState()
    assert settings.appVersion == "0.1.0"
    assert settings.updateStatus == "Update failed. Try again"
    assert not settings.updatePendingInstall

    active.version = Version("0.1.1")
    _write_update_status(tmp_path, "successful", "0.1.1")
    settings.refreshUpdateState()
    assert settings.appVersion == "0.1.0"
    assert not settings.hasUpdate
    assert settings.updateStatus == "Restart required to load the active release"

    restarted_app, restarted = start("0.1.1")
    restarted_app.device.available_update = _available_release("0.1.1")
    restarted.refreshUpdateState()
    assert restarted.appVersion == "0.1.1"
    assert restarted.updateStatus == "Software is up to date"
    assert not restarted.hasUpdate


def test_update_controller_missing_metadata_and_empty_check(update_controller, tmp_path):
    start, _ = update_controller
    (tmp_path / "status.json").write_text("[]", encoding="utf-8")
    app, settings = start("0.1.9")
    assert settings.appVersion == "0.1.9"
    assert settings.updateStatus == "Check for a software update"
    app.device.available_update = _available_release("0.1.10")
    settings.refreshUpdateState()
    assert settings.hasUpdate

    app.device.available_update = None
    app.deviceOperationFinished.emit("update_check")
    assert settings.updateStatus == "Software is up to date"


def test_update_controller_allows_retry_after_staged_install_fails(update_controller, tmp_path):
    start, active = update_controller
    active.version = Version("0.1.0")
    app, settings = start("0.1.0")
    release = _available_release("0.1.1")
    app.device.available_update = release
    app.device.start = Mock()
    app.device.operation = "update_download"
    app.device.future = Future()
    staged = tmp_path / "staged" / "0.1.1"
    app.device.future.set_result((app.device.generation, staged))
    app._on_tick()
    app.device.start.assert_called_once_with("update_install", staged=str(staged))

    _write_update_status(tmp_path, "failed", "")
    settings.refreshUpdateState()
    assert settings.updateStatus == "Update failed. Try again"
    assert not settings.updatePendingInstall
    settings.downloadUpdate()
    assert app.device.start.call_args.args == ("update_download",)
    assert app.device.start.call_args.kwargs == {"update": release}


def test_update_qml_refreshes_on_entry_and_after_state_changes(update_controller, qapp, tmp_path, qt_owner):
    start, active = update_controller
    active.version = Version("0.1.1")
    app, settings = start("0.1.1")
    app.device.available_update = _available_release("0.1.1", architecture="wrong")

    engine = QQmlApplicationEngine(parent=qt_owner)
    qml_dir = Path("app/ui_qt/qml").resolve()
    engine.addImportPath(str(qml_dir))
    engine.rootContext().setContextProperty("appController", app)
    engine.rootContext().setContextProperty("settingsController", settings)
    engine.load(QUrl.fromLocalFile(str(qml_dir / "screens" / "SoftwareUpdateScreen.qml")))
    try:
        screen, = engine.rootObjects()
        status = screen.findChild(QObject, "softwareUpdateStatus")
        current = screen.findChild(QObject, "softwareCurrentVersion")
        available = screen.findChild(QObject, "softwareAvailableVersion")
        install = screen.findChild(QObject, "softwareInstallButton")
        warning = screen.findChild(QObject, "softwareCompatibilityWarning")
        progress = screen.findChild(QObject, "softwareUpdateProgress")
        progress_label = screen.findChild(QObject, "softwareUpdateProgressLabel")
        assert status.property("text") == "Software is up to date"
        assert current.property("text") == "Current version · v0.1.1"
        assert available.property("text") == "Raspberry Pi OS · 64-bit"
        assert not install.property("visible")
        assert not warning.property("visible")
        assert not progress.property("visible")

        app.device.operation = "update_check"
        app.device.future = Future()
        settings.refreshUpdateState()
        assert status.property("text") == "Checking for updates"
        app.device.future.set_result((app.device.generation, _available_release("0.1.2")))
        app._on_tick()
        qapp.processEvents()
        assert status.property("text") == "New version available"
        assert available.property("text") == "Available version · v0.1.2"
        assert install.property("visible")
        assert install.property("enabled")

        app.device.operation = "update_download"
        app.device.future = Future()
        app.device.update_work = ("downloading", 1.0)
        settings.refreshUpdateState()
        assert status.property("text") == "Downloading update"
        assert progress.property("progress") == 1
        assert progress_label.property("text") == "Downloaded · 100%"
        app.device.update_work = ("verifying", 0.25)
        settings.refreshUpdateState()
        assert status.property("text") == "Verifying update"
        assert progress.property("progress") == 0.25
        app.device.update_work = ("checking_archive", None)
        settings.refreshUpdateState()
        assert progress.property("visible") and progress.property("indeterminate")
        app.device.update_work = ("extracting", 0.5)
        settings.refreshUpdateState()
        assert status.property("text") == "Preparing installation"
        assert progress.property("visible") and not progress.property("indeterminate")
        assert progress.property("progress") == 0.5
        assert progress_label.property("text") == "Extracted · 50%"
        app.device.future = None

        _write_update_status(tmp_path, "installing", "0.1.2")
        settings.refreshUpdateState()
        assert status.property("text") == "Installing update"
        assert not install.property("visible")
        assert progress.property("visible") and progress.property("indeterminate")
        _write_update_status(tmp_path, "installing", "0.1.2", step="installing_dependencies")
        settings.refreshUpdateState()
        assert status.property("text") == "Installing dependencies"
        assert progress.property("progress") == pytest.approx(2 / 6)
        assert progress_label.property("text") == "2 of 6 installation steps complete"
        _write_update_status(tmp_path, "installing", "0.1.2", step="activating_release")
        settings.refreshUpdateState()
        assert progress.property("progress") == pytest.approx(5 / 6)
        _write_update_status(tmp_path, "rolled_back", "0.1.2")
        settings.refreshUpdateState()
        assert status.property("text") == "Update failed. Previous version restored"
        assert current.property("text") == "Current version · v0.1.1"
        assert install.property("visible")
        assert not progress.property("visible")

        active.version = Version("0.1.2")
        _write_update_status(tmp_path, "successful", "0.1.2")
        settings.refreshUpdateState()
        assert status.property("text") == "Restart required to load the active release"
        assert current.property("text") == "Current version · v0.1.1"
        assert available.property("text") == "Active release · v0.1.2"
        assert not install.property("visible")
    finally:
        close_qml(engine, app)


def test_responsive_window_sizing(qapp, tmp_path, mock_repo, qt_owner):
    """Verify QML layout responsiveness at 800x480 and 800x600."""
    db_path = tmp_path / "test.db"
    db_path.touch()

    config = AppConfig(database_path=db_path)
    creds = CredentialStore(tmp_path / "creds.json")

    engine = QQmlApplicationEngine(parent=qt_owner)
    qml_dir = Path("app/ui_qt/qml").resolve()
    engine.addImportPath(str(qml_dir))

    app_ctrl = AppController(db_path, config, creds, parent=qt_owner)
    app_ctrl.startup_session.repository = mock_repo
    app_ctrl.startup_session.complete = True
    app_ctrl._initialize_runtime()

    ctx = engine.rootContext()
    ctx.setContextProperty("appController", app_ctrl)
    ctx.setContextProperty("profileController", ProfileController(app_ctrl, parent=app_ctrl))
    ctx.setContextProperty("libraryController", LibraryController(app_ctrl, parent=app_ctrl))
    ctx.setContextProperty("assessmentController", AssessmentController(app_ctrl, parent=app_ctrl))
    ctx.setContextProperty("settingsController", SettingsController(app_ctrl, parent=app_ctrl))

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

    close_qml(engine, app_ctrl)


def test_all_qml_screens_compile_cleanly(qapp, tmp_path, mock_repo, qt_owner):
    """Instantiate all screens, reusable components and App; catch asset warnings."""
    from PySide6.QtCore import QEvent, qInstallMessageHandler
    from PySide6.QtQml import QQmlComponent

    db_path = tmp_path / "test_screens.db"
    config = AppConfig(database_path=db_path)
    creds = CredentialStore(tmp_path / "creds.json")
    engine = QQmlApplicationEngine(parent=qt_owner)
    qml_dir = Path("app/ui_qt/qml").resolve()
    engine.addImportPath(str(qml_dir))
    app_ctrl = AppController(db_path, config, creds, parent=qt_owner)
    app_ctrl.startup_session.repository = mock_repo
    app_ctrl.startup_session.complete = True
    app_ctrl._initialize_runtime()
    app_ctrl._poll_timer.stop()
    controllers = {
        "appController": app_ctrl,
        "profileController": ProfileController(app_ctrl, parent=app_ctrl),
        "libraryController": LibraryController(app_ctrl, parent=app_ctrl),
        "assessmentController": AssessmentController(app_ctrl, parent=app_ctrl),
        "settingsController": SettingsController(app_ctrl, parent=app_ctrl),
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
            props = {"subject": "Biology"} if path.name == "SubjectCard.qml" else {}
            obj = component.createWithInitialProperties(props)
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
        try:
            close_qml(engine, app_ctrl)
        finally:
            qInstallMessageHandler(previous)


def test_navigation_routes_and_error_boundary(qapp, tmp_path, mock_repo, qt_owner):
    """Verify navigating across all reported routes loads without Loader error."""
    from PySide6.QtCore import QCoreApplication

    db_path = tmp_path / "test_routes.db"
    db_path.touch()
    config = AppConfig(database_path=db_path)
    creds = CredentialStore(tmp_path / "creds.json")

    engine = QQmlApplicationEngine(parent=qt_owner)
    qml_dir = Path("app/ui_qt/qml").resolve()
    engine.addImportPath(str(qml_dir))

    app_ctrl = AppController(db_path, config, creds, parent=qt_owner)
    app_ctrl.startup_session.repository = mock_repo
    app_ctrl.startup_session.complete = True
    app_ctrl._initialize_runtime()
    app_ctrl._poll_timer.stop()

    ctx = engine.rootContext()
    ctx.setContextProperty("appController", app_ctrl)
    ctx.setContextProperty("profileController", ProfileController(app_ctrl, parent=app_ctrl))
    ctx.setContextProperty("libraryController", LibraryController(app_ctrl, parent=app_ctrl))
    ctx.setContextProperty("assessmentController", AssessmentController(app_ctrl, parent=app_ctrl))
    ctx.setContextProperty("settingsController", SettingsController(app_ctrl, parent=app_ctrl))

    engine.load(QUrl.fromLocalFile(str(qml_dir / "App.qml")))
    assert len(engine.rootObjects()) > 0
    win = engine.rootObjects()[0]
    screen_loader = win.findChild(QObject, "screenLoader")
    assert screen_loader is not None

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
        assert screen_loader.property("item") is not None, f"Screen did not load for route '{route}'"

    close_qml(engine, app_ctrl)


def test_practice_model_updates_download_status_without_rebuilding_rows(qapp):
    from PySide6.QtTest import QSignalSpy

    from app.ui_qt.controllers.practice_pack_model import PracticePackModel

    model = PracticePackModel()
    changed = QSignalSpy(model.dataChanged)
    resets = QSignalSpy(model.modelReset)
    inserts = QSignalSpy(model.rowsInserted)
    rows = [{"id": "biology", "version": 1, "status": "Available"},
            {"id": "chemistry", "version": 1, "status": "Available"}]
    model.set_rows(rows)
    assert inserts.count() == 1 and model.rowCount() == 2

    model.set_rows([rows[0], {**rows[1], "status": "Downloading", "isDownloading": True}])
    roles = {name: role for role, name in model.roleNames().items()}
    first, last, changed_roles = changed.at(0)
    assert first.row() == last.row() == 1
    assert set(changed_roles) == {roles[b"packStatus"], roles[b"packDownloading"]}
    assert model.data(first, roles[b"packStatus"]) == "Downloading"
    assert resets.count() == 0 and inserts.count() == 1


def test_offline_pack_to_question_flow(qapp, tmp_path, mock_repo, qt_owner):
    """Verify offline downloaded pack -> test setup -> start test -> question -> answers."""
    db_path = tmp_path / "test_flow.db"
    db_path.touch()
    config = AppConfig(database_path=db_path)
    creds = CredentialStore(tmp_path / "creds.json")

    app_ctrl = AppController(db_path, config, creds, parent=qt_owner)
    app_ctrl.startup_session.repository = mock_repo
    app_ctrl.startup_session.complete = True
    app_ctrl._initialize_runtime()

    lib_ctrl = LibraryController(app_ctrl, parent=app_ctrl)
    assess_ctrl = AssessmentController(app_ctrl, parent=app_ctrl)

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



def test_background_removal_refreshes_qt_models_and_session(qapp, tmp_path, qt_owner):
    from app.content.importer import import_pack
    from app.data.repo import Repository
    from tests.content.test_profile_library import metadata, setup

    path = tmp_path / "reconciliation.db"
    with Repository(path) as repo:
        link = setup(repo)
        pack = import_pack(Path("content/sample_biology.json"), repo).pack.question_set
        repo.cache_profile_library("a", link, [metadata(Path("content/sample_biology.json").read_bytes())])
        ctrl = AppController(path, AppConfig(database_path=path), CredentialStore(tmp_path / "creds.json"), parent=qt_owner)
        ctrl.startup_session.repository = repo
        ctrl.startup_session.complete = True
        ctrl._initialize_runtime()
        library = LibraryController(ctrl, parent=ctrl)
        assessment = AssessmentController(ctrl, parent=ctrl)
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


def test_runtime_switch_isolates_profile_state_and_preserves_offline_attempts(qapp, tmp_path, qt_owner):
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
        ctrl = AppController(path, AppConfig(database_path=path), CredentialStore(tmp_path / "cred.json"), parent=qt_owner)
        ctrl.startup_session.repository = repo
        ctrl.startup_session.complete = True
        ctrl._initialize_runtime()
        profiles = ProfileController(ctrl, parent=ctrl)
        library = LibraryController(ctrl, parent=ctrl)
        assessment = AssessmentController(ctrl, parent=ctrl)
        settings = SettingsController(ctrl, parent=ctrl)
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


def test_authenticated_contact_notifies_header_and_settings_without_restart(qapp, tmp_path, qt_owner):
    import httpx

    from app.api.client import DeviceApi
    from app.auth.credentials import DeviceCredential
    from app.data.repo import Repository

    path = tmp_path / "status.db"
    config = AppConfig(database_path=path, api_base_url="https://cloud.test")
    store = CredentialStore(tmp_path / "credentials.json")
    store.save(DeviceCredential("device", "token"))
    with Repository(path) as repo:
        ctrl = AppController(path, config, store, parent=qt_owner)
        ctrl.device.start = lambda *args, **kwargs: None
        ctrl.startup_session.repository = repo
        ctrl.startup_session.complete = True
        ctrl._initialize_runtime()
        settings = SettingsController(ctrl, parent=ctrl)
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


def test_qml_unlink_controls_wait_for_confirmation_and_reconcile(qapp, tmp_path, monkeypatch, qt_owner):
    from threading import Event

    import httpx
    from PySide6.QtCore import QMetaObject
    from PySide6.QtTest import QTest

    from app.auth import account_device
    from app.auth.credentials import DeviceCredential
    from app.data.repo import Repository
    from tests.content.test_profile_library import setup

    path = tmp_path / "unlink.db"
    repo = Repository(path)
    setup(repo)
    account = repo.get_student_account_context()["cloud_account_id"]
    profile = repo.get_profile("a")
    store = CredentialStore(tmp_path / "unlink-credentials.json")
    store.save(DeviceCredential("test-device", "device_test.secret"))
    config = AppConfig(database_path=path, api_base_url="https://unlink.test")
    link = repo.get_profile_link_context("a")["link_id"]
    original = account_device.unlink_relationship
    release = Event()
    account_result = "offline"

    def endpoint(request):
        if request.url.path.endswith("profile-links/unlink"):
            assert release.wait(5)
            return httpx.Response(200, json={"status": "revoked", "link_id": link,
                "student_account_id": account, "study_profile_id": profile.cloud_profile_id,
                "local_profile_id": "a", "account_display_name": "Account", "study_profile_name": "Student A"})
        if account_result == "offline":
            raise httpx.ConnectError("offline", request=request)
        return httpx.Response(200, json={"status": "disconnected"})

    def unlink(*args, **kwargs):
        return original(*args, **kwargs, transport=httpx.MockTransport(endpoint))

    monkeypatch.setattr(account_device, "unlink_relationship", unlink)
    app = AppController(path, config, store, parent=qt_owner)
    app._poll_timer.stop()
    app.startup_session.repository = repo
    app.startup_session.complete = True
    start = app.device.start
    monkeypatch.setattr(app.device, "start", lambda operation, **args: (
        start(operation, **args) if operation in {"profile_unlink", "account_disconnect", "unlink_retry"} else None))
    app._initialize_runtime()
    profile_ctrl = ProfileController(app, parent=app)
    library = LibraryController(app, parent=app)
    assessment = AssessmentController(app, parent=app)
    settings = SettingsController(app, parent=app)
    quick_add = QuickAddController(app, parent=app)
    engine = QQmlApplicationEngine(parent=qt_owner)
    qml = Path("app/ui_qt/qml").resolve()
    engine.addImportPath(str(qml))
    for name, controller in (("appController", app), ("profileController", profile_ctrl),
            ("libraryController", library), ("assessmentController", assessment),
            ("settingsController", settings), ("quickAddController", quick_add)):
        engine.rootContext().setContextProperty(name, controller)

    def finish_job():
        for _ in range(100):
            app._on_tick()
            qapp.processEvents()
            if not app.device.busy:
                return
            QTest.qWait(10)
        pytest.fail("Unlink job did not finish")

    try:
        profile_ctrl.selectProfileId("b")
        app.navigate("account")
        engine.load(QUrl.fromLocalFile(str(qml / "App.qml")))
        window = engine.rootObjects()[0]
        qapp.processEvents()
        assert settings.accountName == repo.get_student_account_context()["display_name"]
        sync_button = window.findChild(QObject, "accountSyncButton")
        assert sync_button.property("text") == "Sync Now"
        with monkeypatch.context() as patch:
            sync = Mock(wraps=app.device.start)
            patch.setattr(app.device, "start", sync)
            assert QMetaObject.invokeMethod(sync_button, "clicked")
            sync.assert_called_once_with("sync")
        dialog = window.findChild(QObject, "unlinkConfirmation")
        assert dialog is not None
        # ListView delegates are visual children rather than QObject children of the window.
        def visual_items(item):
            yield item
            for child in item.childItems():
                yield from visual_items(child)

        buttons = [item for item in visual_items(window.contentItem()) if item.objectName() == "unlinkProfileButton"]
        assert len(buttons) == 2
        assert QMetaObject.invokeMethod(buttons[0], "clicked")
        assert dialog.property("profileId") == "a"
        assert QMetaObject.invokeMethod(dialog, "accept")
        assert settings.unlinkStatus == "Unlinking profile..."
        assert repo.get_profile("a").link_state == "linked"
        release.set()
        finish_job()
        assert [p["id"] for p in profile_ctrl.profiles] == ["b"]
        assert app.activeProfileName == "Student B"
        assert settings.unlinkStatus == "Study Profile unlinked."

        account_button = window.findChild(QObject, "unlinkAccountButton")
        assert QMetaObject.invokeMethod(account_button, "clicked")
        assert not dialog.property("profileId")
        assert QMetaObject.invokeMethod(dialog, "accept")
        finish_job()
        assert settings.unlinkPending and "pending" in settings.unlinkStatus
        assert settings.hasAccount and app.screen == "account"

        account_result = "connected"
        settings.retryUnlink()
        finish_job()
        assert app.screen == "pairing"
        assert not settings.hasAccount and not settings.isPaired
        assert not profile_ctrl.profiles and not assessment.historyList
        assert not app.canGoBack and not profile_ctrl.canAddProfile
        app.goBack()
        assert app.screen == "pairing"
        app.navigate("create_profile")
        assert app.screen == "pairing"
    finally:
        release.set()
        close_qml(engine, app)


def test_last_profile_highlight_and_revoked_pin_target(qapp, tmp_path, qt_owner):
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
        ctrl = AppController(path, AppConfig(database_path=path), CredentialStore(tmp_path / "creds.json"), parent=qt_owner)
        ctrl.startup_session.repository = repo
        ctrl.startup_session.complete = True
        ctrl._initialize_runtime()
        profiles = ProfileController(ctrl, parent=ctrl)
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
        ctrl = AppController(path, AppConfig(database_path=path), CredentialStore(tmp_path / "creds.json"), parent=qt_owner)
        ctrl.startup_session.repository = repo
        ctrl.startup_session.complete = True
        ctrl._initialize_runtime()
        assert ctrl.screen == "profile_picker"
        assert ctrl.ui_controller.selected_profile.id == "b"
        ctrl.close()


def test_auto_sync_toggle_persists_and_manual_sync_remains_available(qapp, tmp_path, qt_owner):
    from unittest.mock import Mock

    from app.data.repo import Repository

    path = tmp_path / "toggle.db"
    with Repository(path) as repo:
        ctrl = AppController(path, AppConfig(database_path=path), CredentialStore(tmp_path / "creds.json"), parent=qt_owner)
        ctrl.repository = repo
        settings = SettingsController(ctrl, parent=ctrl)
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


def test_qt_library_download_uses_the_selected_study_profile(qapp):
    from app.content.catalog import RemotePack
    from tests.content.test_profile_library import metadata

    pack = RemotePack.from_dict(metadata(Path("content/sample_biology.json").read_bytes()))
    app = Mock()
    app.ui_controller.remote_packs = (pack,)
    app.ui_controller.selected_profile = Profile("selected", "Student")
    app.ui_controller.authorized_profile = "selected"
    app.ui_controller.question_sets = ()
    app.repository = None
    app.device.busy = False

    LibraryController(app).downloadPack(pack.set_id, pack.version)

    app.device.start.assert_called_once_with("download", scope=("selected", ""), pack=pack,
                                             local_profile_id="selected")


def test_unpaired_profile_creation_requires_an_account(qapp, tmp_path, monkeypatch, qt_owner):
    """Only operator mode can start anonymous offline practice."""
    from app.data.repo import Repository

    db_path = tmp_path / "offline_profile.db"
    monkeypatch.delenv("ASSESS_MAINTENANCE", raising=False)
    with Repository(db_path) as repo:
        config = AppConfig(database_path=db_path, api_base_url=None)
        ctrl = AppController(db_path, config, CredentialStore(tmp_path / "creds.json"), parent=qt_owner)
        ctrl.startup_session.repository = repo
        ctrl.startup_session.complete = True
        ctrl._initialize_runtime()

        prof_ctrl = ProfileController(ctrl, parent=ctrl)

        # Signal test
        received_text = []
        ctrl.keyboardSubmitted.connect(lambda text: received_text.append(text))
        ctrl.submitKeyboard("Test Student")
        assert received_text == ["Test Student"]
        assert not ctrl.keyboardVisible

        prof_ctrl.createProfile("Alice Learner", "Primary 5")
        prof_ctrl.startTestingMode()
        assert not prof_ctrl.canAddProfile
        assert not repo.list_profiles()
        assert ctrl.screen == "pairing"
        assert "Connect your account" in ctrl.message

        monkeypatch.setenv("ASSESS_MAINTENANCE", "1")
        prof_ctrl.startTestingMode()
        assert ctrl.screen == "home"
        assert ctrl.activeProfileName != ""

        ctrl.close()


def test_qml_pairing_retries_and_loads_existing_account_profiles(qapp, tmp_path, monkeypatch, qt_owner):
    from uuid import uuid4

    import httpx
    from PySide6.QtCore import QEvent, QMetaObject
    from PySide6.QtTest import QTest

    from app.api.client import DeviceApi
    from app.auth import account_device
    from app.auth.pairing import PairingClient
    from app.data.repo import Repository

    monkeypatch.delenv("ASSESS_MAINTENANCE", raising=False)
    path = tmp_path / "pairing.db"
    api_url = "https://pairing.test"
    account_id, session_id = str(uuid4()), str(uuid4())
    profiles = []
    for name in ("Learner One", "Learner Two"):
        profile_id = str(uuid4())
        profiles.append({"id": profile_id, "local_profile_id": "cloud-" + profile_id,
                         "name": name, "account_id": account_id, "link_id": str(uuid4())})
    calls = []
    pairing_approved = False

    def endpoint(request):
        route = request.url.path
        calls.append(route)
        if route == "/api/v1/pairing/request":
            if calls.count(route) == 1:
                return httpx.Response(503, json={"detail": "Database temporarily unavailable"})
            return httpx.Response(201, json={"session_id": session_id, "pairing_code": "123456",
                                             "claim_secret": "test-claim", "expires_at": "2030-01-01T00:00:00Z"})
        if route.endswith("/status"):
            return httpx.Response(200, json={"status": "approved" if pairing_approved else "pending"})
        if route.endswith("/claim"):
            return httpx.Response(200, json={"credential": "device_test.secret"})
        assert route == "/api/v1/device-account"
        if calls.count(route) == 1:
            return httpx.Response(503, json={"detail": "Database temporarily unavailable"})
        return httpx.Response(200, json={"account_id": account_id, "display_name": "Existing Account",
                                         "profiles": profiles, "profile_count": 2, "profile_limit": 3})

    transport = httpx.MockTransport(endpoint)
    monkeypatch.setattr(DeviceApi, "pairing", lambda self: PairingClient(api_url, transport=transport))
    sync_account = account_device.sync_account
    monkeypatch.setattr(account_device, "sync_account", lambda *args, **kwargs: (
        sync_account(*args, **kwargs, transport=transport)))

    app = AppController(path, AppConfig(database_path=path, api_base_url=api_url),
                        CredentialStore(tmp_path / "pairing-credentials.json"), parent=qt_owner)
    app._poll_timer.stop()
    app.startup_session.repository = Repository(path)
    app.startup_session.complete = True
    start = app.device.start
    monkeypatch.setattr(app.device, "start", lambda operation, **args: (
        start(operation, **args) if operation in {"pair_request", "pair_poll", "account_sync"} else None))
    app._initialize_runtime()
    profile_ctrl = ProfileController(app, parent=app)
    settings = SettingsController(app, parent=app)
    engine = QQmlApplicationEngine(parent=qt_owner)
    qml = Path("app/ui_qt/qml").resolve()
    engine.addImportPath(str(qml))
    for name, controller in (("appController", app), ("profileController", profile_ctrl),
            ("libraryController", LibraryController(app, parent=app)),
            ("assessmentController", AssessmentController(app, parent=app)),
            ("settingsController", settings), ("quickAddController", QuickAddController(app, parent=app))):
        engine.rootContext().setContextProperty(name, controller)

    def wait_for(predicate):
        for _ in range(300):
            app._on_tick()
            qapp.processEvents()
            if predicate():
                return
            QTest.qWait(10)
        pytest.fail(f"Pairing stopped on {app.screen}: {settings.pairingStatus} ({calls})")

    try:
        engine.load(QUrl.fromLocalFile(str(qml / "App.qml")))
        window = engine.rootObjects()[0]
        wait_for(lambda: bool(settings.pairingError))
        status = window.findChild(QObject, "pairingStatusText")
        assert "temporarily unavailable" in status.property("text")
        assert not profile_ctrl.canAddProfile

        app.navigate("profile_picker")
        assert not window.findChild(QObject, "createStudyProfileCard").property("visible")
        connect = window.findChild(QObject, "connectExistingAccountButton")
        assert connect.property("visible") and QMetaObject.invokeMethod(connect, "clicked")
        assert app.screen == "pairing"
        qapp.sendPostedEvents(None, QEvent.DeferredDelete)
        qapp.processEvents()

        retry = window.findChild(QObject, "pairingRetryButton")
        assert QMetaObject.invokeMethod(retry, "clicked")
        wait_for(lambda: settings.pairingCode == "123456" and not app.device.busy)
        pairing_approved = True
        app.ui_controller.next_pair_poll = 0
        wait_for(lambda: bool(settings.pairingError) and settings.canRetryAccountSync)
        assert not profile_ctrl.canAddProfile
        assert retry.property("text") == "Retry Profile Sync"
        assert QMetaObject.invokeMethod(retry, "clicked")
        wait_for(lambda: app.screen == "profile_picker")
        assert [p["name"] for p in profile_ctrl.profiles] == ["Learner One", "Learner Two"]
        assert len(app.repository.list_profiles()) == 2
        assert window.findChild(QObject, "createStudyProfileCard").property("visible")
        assert calls.count("/api/v1/pairing/request") == 2
    finally:
        close_qml(engine, app)


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


def test_offline_qt_assessment_survives_restart_and_history_review(qapp, tmp_path, request, qt_owner):
    """Run the native QML assessment against a disposable SQLite database offline."""
    import hashlib
    import json
    import time
    from datetime import UTC, timedelta
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
    repo.cache_student_account_context(account_id, "Offline Account")
    repo.set_setting("account_profiles", json.dumps({"profiles": [{"local_profile_id": profile.id}]}))
    repo.close()

    def launch():
        app_ctrl = AppController(database, config, credentials, parent=qt_owner)
        offline_repository = Repository(database)
        offline_repository.set_setting("connectivity_cloud", json.dumps({"state": "Offline"}))
        offline_repository.set_setting("connectivity_sync", "Offline")
        app_ctrl.startup_session.repository = offline_repository
        app_ctrl.startup_session.complete = True
        app_ctrl._initialize_runtime()
        app_ctrl._poll_timer.stop()  # no connectivity probes or background network activity
        profile_ctrl = ProfileController(app_ctrl, parent=app_ctrl)
        library_ctrl = LibraryController(app_ctrl, parent=app_ctrl)
        assessment_ctrl = AssessmentController(app_ctrl, parent=app_ctrl)
        settings_ctrl = SettingsController(app_ctrl, parent=app_ctrl)
        quick_add_ctrl = QuickAddController(app_ctrl, parent=app_ctrl)
        engine = QQmlApplicationEngine(parent=qt_owner)
        warnings = []
        engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
        closed = False

        def close():
            nonlocal closed
            if not closed:
                closed = True
                close_qml(engine, app_ctrl)
                assert not warnings, "\n".join(warnings)

        request.addfinalizer(close)
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
        return app_ctrl, library_ctrl, assessment_ctrl, settings_ctrl, engine, close

    app_ctrl, library_ctrl, assessment_ctrl, settings_ctrl, engine, close = launch()
    assert app_ctrl.config.api_base_url is None
    assessment_ctrl.startTest("practice", 0, 3, "", "", False)
    time.sleep(1.1)  # ensure persisted practice duration has visible sub-minute evidence
    assessment_ctrl.selectAnswer("A")
    assessment_ctrl.setConfidence("sure")
    assessment_ctrl.selectAnswer("A")
    assessment_ctrl.setConfidence("guessing")
    # Open confirmation from the question grid with the last response skipped.
    app_ctrl.navigate("question_nav")
    review_window = engine.rootObjects()[0]
    modal = review_window.findChild(QObject, "submitConfirmLoader")
    assert modal.property("item") is None

    def key_press(name, key):
        button = review_window.findChild(QObject, name)
        button.forceActiveFocus(Qt.FocusReason.TabFocusReason)
        QTest.keyClick(review_window, key)
        qapp.processEvents()

    key_press("navigatorSubmitButton", Qt.Key.Key_Space)
    assert app_ctrl.screen == "submit_confirm" and modal.property("item") is not None
    QTest.keyClick(review_window, Qt.Key.Key_Escape)
    qapp.processEvents()
    assert app_ctrl.screen == "question" and modal.property("item") is None
    app_ctrl.navigate("question_nav")
    key_press("navigatorSubmitButton", Qt.Key.Key_Return)
    key_press("confirmAssessmentButton", Qt.Key.Key_Return)
    assert app_ctrl.screen == "result"
    assert "submit_confirm" not in app_ctrl._screen_history
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
    QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(592, 164))
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
    close()

    app_ctrl, library_ctrl, assessment_ctrl, settings_ctrl, engine, close = launch()
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
    latest_completed = max(item.completed_at for item in app_ctrl.ui_controller.history_items)
    if latest_completed.tzinfo is None:
        latest_completed = latest_completed.replace(tzinfo=UTC)

    web_started_at = latest_completed + timedelta(seconds=1)
    web_completed_at = web_started_at + timedelta(minutes=2)

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
        "started_at": web_started_at.isoformat(),
        "completed_at": web_completed_at.isoformat(),
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
    close()


def test_practice_filters_expose_count_presets_and_allow_empty_matches(qapp, mock_repo):
    app = Mock()
    app.repository = mock_repo
    app.ui_controller.question_sets = mock_repo.visible_question_sets.return_value
    app.ui_controller.selected_profile = mock_repo.list_profiles.return_value[0]
    controller = LibraryController(app)
    controller._selected_pack_id = "bio-pack-01"
    controller._selected_pack_version = 1

    assert controller.practiceQuestionCount("All topics", "Any difficulty") == 1
    assert controller.practiceCountPresets("All topics", "Any difficulty") == ["All questions", "Custom"]
    assert controller.practiceQuestionCount("Fractions", "Standard") == 0
    assert controller.practiceCountPresets("Fractions", "Standard") == []


def test_qml_library_screen_flow_and_profile_scoped_bank_download(qapp, tmp_path, monkeypatch, qt_owner):
    from datetime import datetime, timedelta
    from threading import Event
    from uuid import uuid4

    import httpx
    from PySide6.QtCore import Q_ARG, QMetaObject, QPoint, Qt
    from PySide6.QtGui import QFont, QFontDatabase
    from PySide6.QtTest import QTest

    from app.api.client import DeviceApi
    from app.auth.credentials import DeviceCredential
    from app.content.client import ContentApiClient
    from app.content.importer import import_pack
    from app.data.repo import Repository
    from app.system.power import battery_label
    from tests.content.test_profile_library import metadata, setup

    for name in ("segoeui.ttf", "segoeuib.ttf", "arial.ttf", "arialbd.ttf", "georgia.ttf", "georgiab.ttf"):
        font_path = Path("C:/Windows/Fonts") / name
        if font_path.exists():
            QFontDatabase.addApplicationFont(str(font_path))
    if os.name == "nt":
        qapp.setFont(QFont("Segoe UI", 11))

    database = tmp_path / "library.db"
    config = AppConfig(database_path=database, api_base_url="https://cloud.test",
                       content_download_directory=tmp_path / "downloads",
                       media_directory=tmp_path / "media")
    credentials = CredentialStore(tmp_path / "creds.json")
    sample = Path("content/sample_biology.json").read_bytes()
    biology = metadata(sample)
    bank_requested = Event()
    hold_download = Event()
    verifying = Event()
    hold_verification = Event()
    state = {"grants": [], "requests": [], "downloads": [], "fail": False, "superseded": False}
    clock = SimpleNamespace(now=datetime(2026, 11, 15, 9).astimezone())
    monkeypatch.setattr("app.ui_qt.controllers.app_controller.datetime", SimpleNamespace(now=lambda: clock.now))
    power = tmp_path / "power_supply"
    (power / "AC").mkdir(parents=True)
    (power / "AC" / "type").write_text("Mains", encoding="ascii")
    (power / "AC" / "online").write_text("1", encoding="ascii")
    monkeypatch.setattr("app.ui_qt.controllers.app_controller.battery_label", lambda: battery_label(power))

    def content_bytes(identifier, subject, chapter, title):
        bank = json.loads(sample)
        bank["set"].update(id=identifier, subject=subject, chapter=chapter, title=title)
        return json.dumps(bank).encode()

    with Repository(database) as seed:
        link_a = setup(seed)
        link_b = seed.get_profile_link_context("b")["link_id"]
        chemistry = [
            content_bytes("chem-bonding", "Chemistry", "Chemical Bonding",
                          "Chemical bonding and molecular structure across ionic and covalent compounds"),
            content_bytes("chem-shapes", "Chemistry", "Chemical Bonding", "Molecular shapes and geometry"),
            content_bytes("chem-periodic", "Chemistry", "Periodic Table", "Periodic trends"),
            content_bytes("chem-carbon", "Chemistry", "Organic Chemistry", "Carbon and its compounds"),
        ]
        maths = content_bytes("math-algebra", "Mathematics", "Algebra", "Linear equations")
        for raw in (*chemistry, maths):
            pack_path = tmp_path / "pack.json"
            pack_path.write_bytes(raw)
            import_pack(pack_path, seed, profile_only=True)
        state["grants"] = [metadata(raw) for raw in chemistry]
        seed.cache_profile_library("a", link_a, state["grants"])
        seed.cache_profile_library("b", link_b, [metadata(maths)])
        previous_day = clock.now - timedelta(days=1)
        for offset in (1, 2):
            finished = previous_day + timedelta(hours=offset)
            attempt_id = str(uuid4())
            seed.create_attempt(Attempt(attempt_id, "a", "chem-bonding", 1,
                                        AttemptStatus.IN_PROGRESS, finished - timedelta(minutes=1)))
            seed.complete_attempt(attempt_id, completed_at=finished, duration_ms=60000, score=0)

    extra_sample = content_bytes("biology-genetics", "Biology", "Genetics", "Molecular genetics")
    extra = metadata(extra_sample)
    jee = metadata(content_bytes("jee-main-motion", "Physics", "Kinematics", "JEE Main: Motion"))
    iat = metadata(content_bytes("iat-motion", "Physics", "Kinematics", "IAT: Motion"))
    public = [biology, metadata(maths), *state["grants"], extra, jee, iat]
    banks = {pack["set_id"]: pack for pack in (biology, extra)}
    scope_requests = []

    class InterruptedStream(httpx.SyncByteStream):
        def __iter__(self):
            midpoint = len(sample) // 2
            yield sample[:midpoint]
            bank_requested.set()
            assert hold_download.wait(8)
            yield sample[midpoint:]

    def handle(request):
        path = request.url.path
        assert request.headers["Authorization"] == "Bearer test-device-token"
        assert path.startswith(f"/api/v1/profile-content/{link_a}/")
        if path.endswith("/question-banks"):
            assert request.url.params["local_profile_id"] == "a"
            filters = dict(request.url.params)
            state["requests"].append(filters)
            exam = filters.get("exam", "")
            matches = [p for p in public if (not exam or p["set_id"].startswith(exam + "-"))
                       and filters["subject"].casefold() in p["subject"].casefold()
                       and filters["chapter"].casefold() in p["chapter"].casefold()
                       and filters["search"].casefold() in p["title"].casefold()]
            return httpx.Response(200, json={"schema_version": 1, "exam": exam, "packs": matches, "next_offset": None})
        if path.endswith("/question-banks/download"):
            body = json.loads(request.content)
            assert (body["local_profile_id"], body["version"]) == ("a", 1)
            pack = banks[body["set_id"]]
            if state["superseded"]:
                public.remove(biology)
                return httpx.Response(409, json={"detail": {"code": "operation_superseded"}})
            state["downloads"].append(pack["set_id"])
            if pack not in state["grants"]:
                state["grants"].append(pack)
            return httpx.Response(200, json=pack)
        if path.endswith("/catalog"):
            return httpx.Response(200, json={"schema_version": 1, "packs": state["grants"], "next_offset": None})
        if path.endswith("/status"):
            body = json.loads(request.content)
            status = body["status"]
            if status == "downloaded" and body["set_id"] == biology["set_id"]:
                verifying.set()
                assert hold_verification.wait(8)
            return httpx.Response(200, json={"status": status})
        if path.endswith(f"/packs/{extra['set_id']}/1"):
            return httpx.Response(200, content=extra_sample)
        assert path.endswith(f"/packs/{biology['set_id']}/1")
        if state["fail"]:
            return httpx.Response(503)
        return httpx.Response(200, stream=InterruptedStream())

    def fake_content(_api, **kwargs):
        scope_requests.append(kwargs)
        return ContentApiClient(config.api_base_url, auth_token="test-device-token",
                                transport=httpx.MockTransport(handle), **kwargs)

    monkeypatch.setattr(DeviceApi, "content", fake_content)
    ctrl = AppController(database, config, credentials, parent=qt_owner)
    ctrl.startup_session.repository = Repository(database)
    ctrl.startup_session.complete = True
    ctrl._initialize_runtime()
    ctrl._poll_timer.stop()
    ctrl._initial_probe_started = True
    ctrl._next_connectivity_check = float("inf")
    credentials.save(DeviceCredential("test-device", "test-device-token"))
    profile = ProfileController(ctrl, parent=ctrl)
    library = LibraryController(ctrl, parent=ctrl)
    assessment = AssessmentController(ctrl, parent=ctrl)
    engine = QQmlApplicationEngine(parent=qt_owner)
    qml_dir = Path("app/ui_qt/qml").resolve()
    engine.addImportPath(str(qml_dir))
    for name, instance in (
        ("appController", ctrl), ("libraryController", library), ("profileController", profile),
        ("assessmentController", assessment), ("settingsController", SettingsController(ctrl, parent=ctrl)),
        ("quickAddController", QuickAddController(ctrl, parent=ctrl)),
    ):
        engine.rootContext().setContextProperty(name, instance)
    warnings = []
    engine.warnings.connect(lambda problems: warnings.extend(p.toString() for p in problems))
    engine.load(QUrl.fromLocalFile(str(qml_dir / "App.qml")))
    assert engine.rootObjects()
    window = engine.rootObjects()[0]
    capture_dir = Path(os.environ.get("QUESTRAA_LIBRARY_CAPTURES", str(tmp_path / "captures")))
    capture_dir.mkdir(parents=True, exist_ok=True)

    def save(name):
        ctrl.clearMessage()
        qapp.processEvents()
        QTest.qWait(70)
        frame = window.grabWindow()
        assert (frame.width(), frame.height()) == (800, 480)
        assert frame.save(str(capture_dir / (name + "-800x480.png")))

    def ready():
        for _ in range(200):
            ctrl._on_tick()
            qapp.processEvents()
            if not ctrl.device.busy and library.bankState != "loading":
                return
            QTest.qWait(25)
        pytest.fail("Timed out waiting for Practice Library")

    def connectivity(cloud, internet):
        ctrl.repository.set_setting("connectivity_cloud", json.dumps({"state": cloud}))
        ctrl.repository.set_setting("connectivity_internet", json.dumps({"state": internet}))
        ctrl.statusChanged.emit()
        library.refreshLibrary()
        library.tick()

    def header_text(name):
        return visual_item(window.contentItem(), name).property("text")

    try:
        profile.selectProfileId("a")
        assert [r["name"] for r in library.homeSubjects] == ["Chemistry"]
        assert window.findChild(QObject, "homeGreeting").property("text") == "Good morning, Student A"
        assert header_text("headerClock") == "15 Nov 2026 · 09:00"
        assert header_text("headerBattery") == "Cable power"
        assert ctrl.practiceStreak == 1
        assert header_text("headerStreak") == "Streak 0"
        assert not visual_item(window.contentItem(), "headerStreakGlow").property("visible")
        assert visual_item(window.contentItem(), "navLabel-progress").property("text") == "Analytics"
        assert visual_item(window.contentItem(), "navIcon-progress").property("source").fileName() == "analytics.svg"

        battery = power / "BAT0"
        battery.mkdir()
        (battery / "type").write_text("Battery", encoding="ascii")
        (battery / "capacity").write_text("73", encoding="ascii")
        assert battery_label(power) == "73%"
        clock.now = clock.now.replace(hour=12)
        ctrl._refresh_clock()
        qapp.processEvents()
        assert ctrl.batteryLabel == "73%"
        assert window.findChild(QObject, "homeGreeting").property("text") == "Good afternoon, Student A"
        assert header_text("headerBattery") == "73%"
        ctrl.repository.cache_completed_results("a", link_a, [{
            "attempt_id": str(uuid4()), "study_profile_id": ctrl.repository.get_profile("a").cloud_profile_id,
            "source": "web", "status": "completed", "title": "Chemistry practice",
            "started_at": (clock.now - timedelta(minutes=1)).isoformat(),
            "completed_at": clock.now.isoformat(), "result": {"score": 0, "maximum_score": 4},
        }])
        ctrl._on_tick()
        clock.now = clock.now.replace(hour=17)
        ctrl._refresh_clock()
        assert window.findChild(QObject, "homeGreeting").property("text") == "Good evening, Student A"
        assert header_text("headerStreak") == "Streak 2"
        assert visual_item(window.contentItem(), "headerStreakGlow").property("visible")
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(45, 271))
        assert ctrl.screen == "progress"
        ctrl.navigate("home")
        save("01-home-chemistry-only")
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(254, 299))
        assert ctrl.screen == "chapters"
        assert library.selectedSubject == "Chemistry"
        save("03-chapters")
        library.selectChapter("Chemical Bonding")
        assert len(library.packs) == 2 and all(p["subject"] == "Chemistry" for p in library.packs)
        save("04-packs")
        library.selectInstalledSubject("Mathematics")
        assert library.selectedSubject == "Mathematics" and library.chapters == [] and library.packs == []
        library.selectPack("math-algebra", 1)
        assert library.selectedPack == {} and library.practiceQuestionTotal == 0
        assessment.startTest()
        assert not assessment.isActive
        ctrl.navigate("subjects")
        save("02-subject-library")
        ctrl.navigate("content")
        connectivity("Offline", "Unavailable")
        save("05-downloaded-offline")
        library.setBrowsingBanks(True)
        library.tick()
        assert library.bankState == "offline"
        save("06-browse-offline")

        connectivity("Online", "Available")
        save("07-catalog-loading")
        ready()
        assert library.bankState == "ready"
        assert {p["subject"] for p in library.questionBanks} == {"Biology", "Chemistry", "Mathematics", "Physics"}
        assert [r["name"] for r in library.homeSubjects] == ["Chemistry"]
        save("08-catalog")
        catalog_grid = window.findChild(QObject, "questionBankGrid")
        assert catalog_grid.property("contentHeight") > catalog_grid.property("height")
        assert catalog_grid.property("cellWidth") * catalog_grid.property("columns") <= catalog_grid.property("width")
        catalog_grid.setProperty("contentY", catalog_grid.property("contentHeight") - catalog_grid.property("height"))
        qapp.processEvents()
        assert catalog_grid.property("contentY") > 0
        exam = window.findChild(QObject, "questionBankExamFilter")
        subject = window.findChild(QObject, "questionBankSubjectFilter")
        assert exam.property("displayText") == "All exams"
        assert subject.property("displayText") == "All subjects"
        assert QMetaObject.invokeMethod(subject, "activated", Qt.ConnectionType.DirectConnection, Q_ARG(int, 2))
        ready()
        assert [p["id"] for p in library.questionBanks] == [jee["set_id"], iat["set_id"]]
        assert QMetaObject.invokeMethod(exam, "activated", Qt.ConnectionType.DirectConnection, Q_ARG(int, 1))
        ready()
        assert [p["id"] for p in library.questionBanks] == [jee["set_id"]]
        assert state["requests"][-1]["offset"] == "0"
        assert exam.property("displayText") == "JEE" and subject.property("displayText") == "Physics"
        save("13-jee-physics")
        library.filterBanks("Cell", "Biology", "")
        ready()
        assert [p["id"] for p in library.questionBanks] == [biology["set_id"]]
        assert state["requests"][-1]["subject"] == "Biology"

        state["superseded"] = True
        library.downloadBank(biology["set_id"], 1)
        ready()
        assert library.bankState == "ready" and library.questionBanks == []
        assert [r["name"] for r in library.homeSubjects] == ["Chemistry"]
        state["superseded"] = False
        public.insert(0, biology)
        library.refreshBanks()
        ready()

        state["fail"] = True
        QTest.qWait(70)
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(261, 215))
        ready()
        assert library.questionBanks[0]["retry"]
        assert [r["name"] for r in library.homeSubjects] == ["Chemistry"]
        state["fail"] = False
        library.filterBanks("", "", "")
        ready()
        library.retryDownload(biology["set_id"], 1)
        assert bank_requested.wait(5)
        library.downloadBank(extra["set_id"], 1)
        library.downloadBank(extra["set_id"], 1)
        ctrl._on_tick()
        assert 0 < library.downloadPercent < 100
        assert library.pendingDownloads == 2
        assert [row["state"] for row in library.downloadQueue] == ["Downloading", "Queued"]
        assert state["downloads"] == [biology["set_id"], biology["set_id"]]
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(400, 83))
        assert library.showingDownloadQueue
        queue_view = window.findChild(QObject, "practiceDownloadQueue")
        assert queue_view.property("visible") and queue_view.property("count") == 2
        save("09-download-in-progress")
        queued_bar = visual_item(queue_view, "practiceQueuedProgress")
        active_bar = visual_item(queue_view, "practiceDownloadProgress")
        assert queued_bar.property("visible") and queued_bar.property("progress") == 0
        assert active_bar.property("visible") and active_bar.property("progress") == library.downloadPercent / 100
        hold_download.set()
        assert verifying.wait(5)
        ctrl._on_tick()
        assert library.downloadQueue[0]["state"] == "Verifying"
        save("10-download-verifying")
        connectivity("Offline", "Unavailable")
        hold_verification.set()
        ready()
        assert library.pendingDownloads == 1
        assert library.downloadQueue[0]["state"] == "Queued"
        assert extra["set_id"] not in state["downloads"]
        ctrl.navigate("home")
        connectivity("Online", "Available")
        ready()
        assert library.pendingDownloads == 0
        assert all(row["state"] == "Ready offline" for row in library.downloadQueue)
        assert state["downloads"] == [biology["set_id"], biology["set_id"], extra["set_id"]]
        assert [r["name"] for r in library.homeSubjects] == ["Biology", "Chemistry"]
        assert len(ctrl.repository.list_question_set_versions(biology["set_id"])) == 1
        library.openDownloadQueue()
        save("11-download-ready")
        assert all(scope == {"local_profile_id": "a", "link_id": link_a} for scope in scope_requests)

        clock.now += timedelta(days=2)
        ctrl._refresh_clock()
        assert ctrl.practiceStreak == 0 and ctrl.localDate == "17 Nov 2026"
        profile.selectProfileId("b")
        assert [r["name"] for r in library.homeSubjects] == ["Mathematics"]
        assert header_text("headerStreak") == "Streak 0"
        assert library.questionBanks == []
        assert library.downloadQueue == []
        library.selectInstalledSubject("Mathematics")
        assert library.chapters == ["Algebra"]
        library.selectChapter("Algebra")
        assert [p["id"] for p in library.packs] == ["math-algebra"]
        ctrl.repository.cache_profile_library("b", link_b, [])
        library.refreshLibrary()
        ctrl.navigate("home")
        assert library.homeSubjects == []
        save("12-home-no-downloads")
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(196, 347))
        assert ctrl.screen == "content" and library.browsingBanks
    finally:
        hold_download.set()
        hold_verification.set()
        close_qml(engine, ctrl)
    assert not warnings, "\n".join(warnings)
