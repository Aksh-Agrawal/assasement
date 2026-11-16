"""Render every Pi route and measure representative local UI work at 800×480."""

import argparse
import ctypes
import gc
import json
import os
import re
import tempfile
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from time import perf_counter_ns
from types import SimpleNamespace

import PySide6
import segno
from PySide6.QtCore import QObject, QPoint, Qt, QUrl
from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest

from app.auth.credentials import CredentialStore, DeviceCredential
from app.config import AppConfig
from app.connectivity import CLOUD_KEY, INTERNET_KEY, WIFI_KEY
from app.content.catalog import RemotePack
from app.core.models import MarkingScheme, Option, Profile, Question, QuestionSet
from app.data.repo import Repository
from app.ui_qt.controllers.app_controller import AppController
from app.ui_qt.controllers.assessment_controller import AssessmentController
from app.ui_qt.controllers.library_controller import LibraryController, PracticeDownload
from app.ui_qt.controllers.profile_controller import ProfileController
from app.ui_qt.controllers.quick_add_controller import QuickAddController
from app.ui_qt.controllers.settings_controller import SettingsController
from app.ui_qt.main import close_qml

SAMPLE_TIME = datetime(2026, 11, 15, 9, 0, tzinfo=UTC)
ACCOUNT = "00000000-0000-4000-8000-000000000001"
ACTIVE_LINK = "00000000-0000-4000-8000-000000000011"


def ms(start):
    return round((perf_counter_ns() - start) / 1_000_000, 2)


def memory_kib():
    if os.name == "nt":
        class ProcessMemory(ctypes.Structure):
            _fields_ = [
                ("size", ctypes.c_ulong), ("faults", ctypes.c_ulong),
                ("peak", ctypes.c_size_t), ("working", ctypes.c_size_t),
                ("remaining", ctypes.c_size_t * 6),
            ]

        counters = ProcessMemory()
        counters.size = ctypes.sizeof(counters)
        current_process = ctypes.c_void_p(-1)
        if ctypes.windll.psapi.GetProcessMemoryInfo(current_process, ctypes.byref(counters), counters.size):
            return {"working": counters.working // 1024, "peak": counters.peak // 1024}
    elif Path("/proc/self/status").is_file():
        status = Path("/proc/self/status").read_text(encoding="utf-8")
        return {name: int(match[1]) for key, name in (("VmRSS", "working"), ("VmHWM", "peak"))
                if (match := re.search(rf"^{key}:\s+(\d+) kB", status, re.MULTILINE))}
    return {}


def bank_row(pack):
    return {
        "set_id": pack.id, "version": pack.version, "title": pack.title,
        "subject": pack.subject, "chapter": pack.chapter,
        "question_count": len(pack.questions), "size_bytes": 1024, "sha256": "0" * 64,
        "published_at": SAMPLE_TIME.isoformat(),
    }


def seed(repo, extra_packs):
    profiles = [
        {"local_profile_id": "alex", "exam_context": "Grade 11"},
        {"local_profile_id": "maya", "exam_context": "Grade 10"},
    ]
    for i, (profile, name) in enumerate(zip(profiles, ("Alex", "Maya"), strict=True), start=1):
        identifier = profile["local_profile_id"]
        repo.create_profile(Profile(identifier, name))
        repo.apply_profile_link(identifier, {
            "local_profile_id": identifier,
            "link_id": f"00000000-0000-4000-8000-00000000001{i}",
            "student_account_id": ACCOUNT,
            "study_profile_id": f"00000000-0000-4000-8000-00000000002{i}",
            "account_display_name": "Alex", "study_profile_name": name, "status": "linked",
        })
    repo.cache_student_account_context(ACCOUNT, "Alex")
    repo.set_setting("account_profiles", json.dumps({"profiles": profiles, "profile_count": 2}))
    source = QuestionSet(
        id="cell-biology", version=1, title="Cell Structure and Organelles",
        subject="Biology", chapter="Cell Biology", marking=MarkingScheme(),
        questions=(
            Question(
                id="q1", position=1, topic="Cell Biology", difficulty=1,
                question_text="Which organelle produces most ATP during aerobic respiration?",
                options=(Option("A", "Mitochondrion"), Option("B", "Chloroplast"),
                         Option("C", "Ribosome"), Option("D", "Golgi apparatus")),
                correct_key="A",
                explanation="Mitochondria produce most of a cell’s ATP through oxidative phosphorylation.",
            ),
            Question(
                id="q2", position=2, topic="Cell Biology", difficulty=2,
                question_text="Which structure distinguishes plant cells from animal cells?",
                options=(Option("A", "Cellulose cell wall"), Option("B", "Nucleus"),
                         Option("C", "Cytoplasm"), Option("D", "Cell membrane")),
                correct_key="A",
                explanation="Plant cells have a cellulose wall outside their cell membrane.",
            ),
        ),
    )
    packs = [source, replace(
        source, id="atomic-structure", title="Atomic Structure and Isotopes",
        subject="Chemistry", chapter="Atomic Theory",
    ), replace(
        source, id="linear-equations", title="Linear Equations and Inequalities",
        subject="Mathematics", chapter="Algebra",
    )]
    for pack in packs:
        repo.import_question_set(pack, content_hash="0" * 64, downloaded_at=SAMPLE_TIME)
    for i in range(extra_packs):
        # Installed on the same device and eligible only to the other learner.
        pack = replace(source, id=f"other-learner-{i:03}", title=f"Private pack {i + 1}")
        repo.import_question_set(pack, content_hash="0" * 64, downloaded_at=SAMPLE_TIME, profile_only=True)
    repo.cache_profile_library("alex", ACTIVE_LINK, [bank_row(pack) for pack in packs])
    repo.cache_profile_library("maya", "00000000-0000-4000-8000-000000000012",
                               [bank_row(replace(source, id=f"other-learner-{i:03}",
                                                 title=f"Private pack {i + 1}"))
                                for i in range(extra_packs)])
    return source


def capture(app, output, work, extra_packs):
    qml_dir = Path(__file__).resolve().parent / "qml"
    expected = set(re.findall(r'return "(screens/[^"]+\.qml)"',
                              (qml_dir / "App.qml").read_text(encoding="utf-8")))
    captures = {}
    measurements = {"navigation_to_grab_ms": {}, "samples_ms": {}, "window_qobjects": {},
                    "process_memory_kib": {},
                    "extra_private_packs": extra_packs, "qt": PySide6.__version__,
                    "platform": app.platformName(), "scenegraph": os.environ.get("QT_QUICK_BACKEND")}
    config = AppConfig(database_path=work / "capture.db", data_directory=work,
                       credential_path=work / "creds.json", api_base_url="https://capture.test",
                       update_root=work / "updates", update_inbox=work / "inbox",
                       media_directory=work / "media", log_directory=work / "logs")
    credentials = CredentialStore(config.credential_path)
    credentials.save(DeviceCredential("sample-device", "fixture-only"))
    ctrl = AppController(config.database_path, config, credentials)
    ctrl._poll_timer.stop()
    ctrl._clock_timer.stop()
    ctrl._local_time = SAMPLE_TIME
    ctrl._battery_label = "Mains"
    ctrl.startup_session.repository = Repository(config.database_path)
    repo = ctrl.startup_session.repository
    try:
        source = seed(repo, extra_packs)
    except BaseException:
        ctrl.close()
        raise
    repo.set_setting(CLOUD_KEY, json.dumps({"state": "Online"}))
    repo.set_setting(INTERNET_KEY, json.dumps({"state": "Available"}))
    repo.set_setting(WIFI_KEY, json.dumps({"state": "connected", "ssid": "Study room"}))
    # Drive the running application’s state without host network, Wi-Fi or update services.
    ctrl.device.account_verified = True
    ctrl.device.pairing = SimpleNamespace(code="K7M2P9")
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(qml_dir))
    warnings = []
    engine.warnings.connect(lambda batch: warnings.extend(item.toString() for item in batch))
    profile = ProfileController(ctrl, parent=ctrl)
    library = LibraryController(ctrl, parent=ctrl)
    assess = AssessmentController(ctrl, parent=ctrl)
    settings = SettingsController(ctrl, parent=ctrl)
    settings._update_timer.stop()
    quick_add = QuickAddController(ctrl, parent=ctrl)
    for name, controller in (
        ("appController", ctrl), ("profileController", profile), ("libraryController", library),
        ("assessmentController", assess), ("settingsController", settings), ("quickAddController", quick_add),
    ):
        engine.rootContext().setContextProperty(name, controller)

    def grab():
        app.processEvents()
        return window.grabWindow()

    def save(name, action=None):
        start = perf_counter_ns()
        if isinstance(action, str):
            ctrl.navigate(action)
            if ctrl.screen != action:
                raise RuntimeError(f"{action} redirected to {ctrl.screen}")
        elif action is not None:
            action()
        ctrl.clearMessage()
        image = grab()
        measurements["navigation_to_grab_ms"][name] = ms(start)
        QTest.qWait(160)
        image = grab()
        source_url = loader.property("source").fileName()
        captures[name] = f"screens/{source_url}"
        if name in {"01-startup", "03-home", "20-bank-ready", "37-virtual-keyboard"}:
            measurements["window_qobjects"][name] = len(window.findChildren(QObject))
            measurements["process_memory_kib"][name] = memory_kib()
        if image.size().toTuple() != (800, 480) or not image.save(str(output / (name + ".png"))):
            raise RuntimeError(f"Could not save 800×480 image {name}")
        print(f"Captured {name} ({source_url})")

    def sample(label, action, repeats=11):
        values = []
        for _ in range(repeats):
            start = perf_counter_ns()
            action()
            values.append(ms(start))
        measurements["samples_ms"][label] = {"median": median(values), "values": values}

    try:
        start = perf_counter_ns()
        engine.load(QUrl.fromLocalFile(str(qml_dir / "App.qml")))
        window = engine.rootObjects()[0]
        assert isinstance(window, QQuickWindow)
        window.setWidth(800)
        window.setHeight(480)
        window.show()
        loader = window.findChild(QObject, "screenLoader")
        grab()
        measurements["qml_load_to_first_grab_ms"] = ms(start)
        save("01-startup")
        start = perf_counter_ns()
        ctrl.startup_session.complete = True
        ctrl._initialize_runtime()
        measurements["initialize_seeded_runtime_ms"] = ms(start)
        save("02-profile-picker", "profile_picker")
        profile.selectProfileId("alex")
        save("03-home", "home")
        save("04-subjects", "subjects")
        save("05-chapters", lambda: library.selectSubject(source.subject))
        save("06-packs", lambda: library.selectChapter(source.chapter))
        save("07-test-setup", lambda: library.selectPack(source.id, 1))
        save("08-question", lambda: assess.startTest("practice", 0))
        save("09-question-detail", "question_detail")
        ctrl.navigate("question")
        leave = window.findChild(QObject, "questionLeaveButton")
        point = leave.mapToScene(leave.boundingRect().center()).toPoint() if leave else QPoint(31, 25)
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=point)
        save("10-leave-confirm")
        question = loader.property("item")
        scrim_point = question.mapToScene(QPoint(10, int(question.height()) - 10)).toPoint()
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=scrim_point)
        save("11-confidence", lambda: assess.selectAnswer("A"))
        assess.setConfidence("sure")
        save("12-question-navigator", "question_nav")
        def request_submit():
            # Use the same engine transition when measuring an earlier checkout.
            if assess._engine.state.value == "IN_QUESTION":
                ctrl.ui_controller.application.request_submit()
            ctrl.navigate("submit_confirm")

        save("13-submit-confirm", request_submit)
        save("14-result", assess.confirmSubmit)
        save("15-review", lambda: assess.openReview("all"))
        save("16-history", "history")
        save("17-analytics", "progress")
        save("18-downloaded", "content")
        save("19-bank-loading", lambda: library.setBrowsingBanks(True))
        remote = tuple(RemotePack.from_dict(bank_row(replace(
            source, id=f"remote-{i:03}", title=f"Cell Biology Practice {i + 1}",
        ))) for i in range(30))
        scope = ("alex", ACTIVE_LINK)
        library._bank_scope = scope

        def bank_state(state, packs=()):
            online = state == "ready"
            repo.set_setting(CLOUD_KEY, json.dumps(
                {"state": "Online" if online else "Offline" if state == "offline" else "Server unavailable"}))
            repo.set_setting(INTERNET_KEY, json.dumps({"state": "Unavailable" if state == "offline" else "Available"}))
            ctrl.statusChanged.emit()
            library._bank_packs = packs
            library._bank_state = state
            library.bankCatalogChanged.emit()

        save("20-bank-ready", lambda: bank_state("ready", remote))
        grid = window.findChild(QObject, "questionBankGrid")
        y = grid.property("originY")

        def scroll_step():
            grid.setProperty("contentY", y + 120 if grid.property("contentY") == y else y)
            grab()

        entry = PracticeDownload(scope, remote[0], "download_bank", state="Downloading")

        def update_row():
            entry.state = "Verifying" if entry.state == "Downloading" else "Downloading"
            library._download_states_changed()
            grab()

        library._downloads[entry.identity] = entry
        sample("catalog_scroll_step_to_grab", scroll_step)
        sample("catalog_status_change_to_grab", update_row)
        library._active_download = entry
        entry.state = "Downloading"
        library._download_percent = 47
        library._download_states_changed()
        save("21-download-queue", library.openDownloadQueue)
        library.setBrowsingBanks(True)
        save("22-bank-offline", lambda: bank_state("offline"))
        save("23-bank-error", lambda: bank_state("unreachable"))
        library.setBrowsingBanks(False)
        quick_add._upload_url = "https://capture.test/quick-add"
        quick_add._short_code = "DEMO42"
        quick_add._profile_name = "Alex"
        quick_add._status_text = "Waiting for your phone to scan."
        segno.make(quick_add._upload_url, micro=False).save(quick_add._qr_file_path, scale=6)
        save("24-quick-add", "quick_add")
        save("25-settings", "settings")
        save("26-wifi", "wifi")
        save("27-sync", "sync")
        save("28-account", "account")
        save("29-software-update", "software_update")
        save("30-device-info", "device_info")
        save("31-diagnostics", "diagnostics")
        save("32-about", "about")
        save("33-institute-work", "institute_work")
        save("34-pairing", "pairing")
        save("35-create-profile", "create_profile")
        save("36-recovery", "recovery")
        ctrl.navigate("create_profile")
        save("37-virtual-keyboard", lambda: ctrl.openKeyboard("profile_name", "", False, "Enter student name"))
        ctrl.keyboardCancelled()
        profile.selectProfileId("maya")
        if not extra_packs:
            save("38-home-empty", "home")
        sample("sqlite_refresh_catalog", ctrl.ui_controller.refresh_catalog)
        profile.selectProfileId("alex")
        sample("sqlite_refresh_active_learner", ctrl.ui_controller.refresh_catalog)

        def navigate_home_and_catalog():
            ctrl.navigate("home")
            grab()
            ctrl.navigate("content")
            grab()

        sample("home_and_practice_round_trip_to_grab", navigate_home_and_catalog)
    finally:
        close_qml(engine, ctrl)

    measurements["captures"] = captures
    measurements["missing_screens"] = sorted(expected - set(captures.values()))
    measurements["qml_warnings"] = warnings
    (output / "measurements.json").write_text(json.dumps(measurements, indent=2) + "\n", encoding="utf-8")
    if measurements["missing_screens"] or warnings:
        print(json.dumps({"missing": measurements["missing_screens"], "qml_warnings": warnings}, indent=2))
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--extra-packs", type=int, default=0)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    os.environ.setdefault("QSG_RENDER_LOOP", "basic")
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication([])
    if os.name == "nt" and app.platformName() == "offscreen":
        fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        for name in ("arial.ttf", "arialbd.ttf", "georgia.ttf", "georgiab.ttf", "segoeui.ttf"):
            if (fonts / name).is_file():
                QFontDatabase.addApplicationFont(str(fonts / name))
        app.setFont(QFont("Arial"))
    with tempfile.TemporaryDirectory(prefix="questraa-ui-review-") as work:
        result = capture(app, args.output, Path(work), args.extra_packs)
        gc.collect()
        return result


if __name__ == "__main__":
    raise SystemExit(main())
