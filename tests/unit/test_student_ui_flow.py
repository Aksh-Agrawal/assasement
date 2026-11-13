"""Document-defined device flow against the real engine and file-backed repository."""

import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from app.auth.credentials import CredentialStore
from app.auth.pin import PinUnlock
from app.config import AppConfig
from app.content.importer import import_pack
from app.core.engine import AssessmentState
from app.core.models import Confidence, Profile
from app.data.repo import Repository
from app.input.actions import Action
from app.ui.controller import UIController
from app.ui.device import DeviceConsole
from app.ui.router import SETTINGS_ROUTES, UIScreen
from app.ui.startup import StartupSession


@pytest.fixture(autouse=True)
def legacy_engine_fixture_mode(monkeypatch):
    monkeypatch.setenv("ASSESS_MAINTENANCE", "1")


def seed(repository):
    import_pack(Path("content/sample_biology.json"), repository, make_active=True)
    repository.create_profile(Profile(id="test-profile", display_name="Local Student"))


def choose(controller, command, value=None):
    index = next(
        i
        for i, item in enumerate(controller.choices)
        if item.command == command and (value is None or item.value == value)
    )
    controller.handle(Action.CONFIRM, ("choice", index))


def student(repository, device=None):
    controller = UIController(repository, startup=True, device=device)
    controller.finish_splash()
    assert controller.screen is UIScreen.PROFILE
    choose(controller, "profile", 0)
    assert controller.screen is UIScreen.HOME
    return controller


def begin(controller):
    choose(controller, "route", UIScreen.SUBJECTS)
    assert controller.screen is UIScreen.SUBJECTS
    choose(controller, "subject", 0)
    assert controller.screen is UIScreen.CHAPTERS
    choose(controller, "chapter", 0)
    assert controller.screen is UIScreen.PACKS
    choose(controller, "pack", 0)
    assert controller.screen is UIScreen.TEST_SETUP
    choose(controller, "start")
    assert controller.screen is UIScreen.QUESTION


def test_student_flow_real_engine_result_review_and_offline_history(tmp_path):
    with Repository(tmp_path / "flow.db") as repo:
        seed(repo)
        controller = student(repo)
        assert not controller.choices[0].enabled
        begin(controller)
        for _index in range(20):
            key = controller.application.current_question().correct_key
            controller.handle(getattr(Action, f"SELECT_{key}"))
            assert controller.screen is UIScreen.CONFIDENCE
            assert (
                repo.get_attempt_responses(controller.application.engine.attempt.id)[
                    -1
                ].selected_key
                == key
            )
            controller.handle(Action.SELECT_A)
            assert controller.screen is UIScreen.QUESTION
            controller.handle(Action.NEXT)
        assert controller.screen is UIScreen.SUBMIT_CONFIRM
        controller.handle(Action.CONFIRM)
        assert controller.screen is UIScreen.QUESTION  # no accidental Enter submission
        controller.handle(Action.SUBMIT)
        controller.handle(Action.SUBMIT)
        assert controller.screen is UIScreen.RESULT
        assert controller.result.correct == 20
        assert controller.result.score == 80
        choose(controller, "review", "wrong")
        assert controller.screen is UIScreen.REVIEW
        assert not controller.review_items
        controller.handle(Action.BACK)
        choose(controller, "review", "all")
        assert len(controller.review_items) == 20
        before = repo.get_attempt_responses(controller.application.engine.attempt.id)
        controller.handle(Action.SELECT_D)
        controller.handle(Action.MARK_REVIEW)
        assert repo.get_attempt_responses(controller.application.engine.attempt.id) == before
        controller.handle(Action.BACK)
        choose(controller, "done")
        choose(controller, "route", UIScreen.PROGRESS)
        assert len(controller.history_items) == 1
        assert controller.history_items[0].score == 80
        assert controller.network_label == "Checking…"


def test_restart_retains_answer_confidence_flag_order_and_original_version(tmp_path):
    path = tmp_path / "resume.db"
    with Repository(path) as repo:
        seed(repo)
        c = student(repo)
        begin(c)
        c.handle(Action.SELECT_B)
        c.handle(Action.SELECT_C)
        c.handle(Action.MARK_REVIEW)
        original_question = c.application.current_question().id
        order = c.application.engine.ordered_question_ids
        original_set = c.application.engine.question_set
        c.handle(Action.NEXT)
        c.handle(Action.SELECT_D)  # interrupted on confidence screen
        attempt_id = c.application.engine.attempt.id
        c.close()
        repo.import_question_set(
            replace(original_set, version=2), content_hash="newer", is_active=True
        )
    with Repository(path) as repo:
        c = student(repo)
        assert c.choices[0].enabled
        choose(c, "resume")
        assert c.application.engine.question_set.version == 1
        assert c.application.engine.ordered_question_ids == order
        saved = repo.get_response(attempt_id, original_question)
        assert saved.selected_key == "B"
        assert saved.confidence is Confidence.GUESSING
        assert saved.marked_review
        assert any(r.selected_key == "D" for r in repo.get_attempt_responses(attempt_id))


def test_pause_menu_home_confirmation_and_question_navigator(tmp_path):
    with Repository(tmp_path / "menu.db") as repo:
        seed(repo)
        c = student(repo)
        begin(c)
        c.handle(Action.MENU)
        assert c.screen is UIScreen.ASSESSMENT_MENU
        choose(c, "navigator")
        c.handle(Action.CONFIRM, ("question", 12))
        assert c.application.engine.current_index == 12
        c.handle(Action.PREV)
        assert c.application.engine.current_index == 11
        c.handle(Action.MENU)
        choose(c, "route", UIScreen.LEAVE_CONFIRM)
        assert c.screen is UIScreen.LEAVE_CONFIRM
        choose(c, "leave")
        assert c.screen is UIScreen.HOME
        assert c.can_resume


def test_empty_profile_requires_cloud_connection_without_anonymous_creation(tmp_path, monkeypatch):
    monkeypatch.delenv("ASSESS_MAINTENANCE")
    with Repository(tmp_path / "profiles.db") as repo:
        c = UIController(repo, startup=True)
        c.finish_splash()
        assert c.screen is UIScreen.PAIRING
        assert not c.profiles
        assert not any(ch.value is UIScreen.ADD_PROFILE for ch in c.choices)
        assert repo.list_profiles() == ()


def test_protected_profile_pin_unlock_and_persistent_lockout(tmp_path):
    with Repository(tmp_path / "pin.db") as repo:
        salt = "fixture-random-salt"
        digest = hashlib.pbkdf2_hmac("sha256", b"7391", salt.encode(), 100_000).hex()
        repo.create_profile(
            Profile(id="p", display_name="Protected"),
            pin_hash=f"pbkdf2_sha256$100000${digest}",
            pin_salt=salt,
        )
        c = UIController(repo, startup=True)
        c.finish_splash()
        choose(c, "profile", 0)
        assert c.screen is UIScreen.PIN
        c.handle_text("7391")
        c.handle(Action.SELECT_D)
        assert c.screen is UIScreen.HOME
        assert c.text_value == ""
        service = PinUnlock(repo, clock=lambda: 1000)
        for _ in range(5):
            assert service.unlock("p", "0000")[0] is False
        assert service.unlock("p", "7391")[0] is False
        assert PinUnlock(repo, clock=lambda: 1031).unlock("p", "7391")[0] is True


def test_unknown_pin_format_never_bypasses_protection(tmp_path):
    with Repository(tmp_path / "pin.db") as repo:
        repo.create_profile(
            Profile(id="p", display_name="Protected"), pin_hash="legacy-opaque", pin_salt="salt"
        )
        c = UIController(repo, startup=True)
        c.finish_splash()
        choose(c, "profile", 0)
        c.handle_text("1234")
        c.handle(Action.SELECT_D)
        assert c.screen is UIScreen.PIN
        assert "recovery" in c.message


@pytest.mark.parametrize("route", SETTINGS_ROUTES)
def test_every_settings_route_is_available_offline_and_returns(tmp_path, route):
    path = tmp_path / "settings.db"
    with Repository(path) as repo:
        seed(repo)
        device = DeviceConsole(path)
        c = student(repo, device)
        choose(c, "route", UIScreen.SETTINGS)
        choose(c, "route", route)
        assert c.screen is route
        c.handle(Action.BACK)
        assert c.screen is UIScreen.SETTINGS


def test_real_startup_and_corrupt_database_recovery(tmp_path):
    path = tmp_path / "startup.db"
    session = StartupSession(
        path, AppConfig(database_path=path), CredentialStore(tmp_path / "credential.json")
    )
    while not session.complete and not session.failed:
        session.advance()
    assert session.complete and not session.failed
    assert len(session.rows) == 9
    assert session.repository.quick_check().ok
    session.close()
    bad = tmp_path / "bad.db"
    bad.write_bytes(b"This is not SQLite")
    original = bad.read_bytes()
    session = StartupSession(
        bad, AppConfig(database_path=bad), CredentialStore(tmp_path / "credential.json")
    )
    for _ in range(12):
        session.advance()
    assert session.failed
    assert bad.read_bytes() == original
    session.close()


def test_background_failure_never_blocks_assessment_or_exposes_exception(tmp_path, monkeypatch):
    import threading

    path = tmp_path / "background.db"
    with Repository(path) as repo:
        seed(repo)
        device = DeviceConsole(path)
        c = student(repo, device)
        begin(c)
        started, release = threading.Event(), threading.Event()

        def slow_failure(operation, **arguments):
            started.set()
            release.wait(5)
            raise RuntimeError("HTTP 500 password=private backend detail")

        monkeypatch.setattr(device, "_execute", slow_failure)
        device.start("diagnostics")
        assert started.wait(2)
        c.handle(Action.SELECT_B)
        c.handle(Action.GUESSING)
        c.handle(Action.NEXT)
        assert c.application.engine.current_index == 1
        release.set()
        with pytest.raises(RuntimeError):
            device.future.result(timeout=3)
        assert c.tick()
        assert "HTTP" not in c.message
        assert "private" not in c.message
        assert c.screen is UIScreen.QUESTION
        assert repo.get_attempt_responses(c.application.engine.attempt.id)[0].selected_key == "B"
        c.close()


def test_diagnostics_and_support_export_use_existing_services_offline(tmp_path):
    import zipfile

    path = tmp_path / "diagnostics.db"
    with Repository(path) as repo:
        seed(repo)
        device = DeviceConsole(
            path,
            AppConfig(
                database_path=path,
                log_directory=tmp_path / "logs",
                update_root=tmp_path / "updates",
            ),
        )
        device.start("diagnostics")
        device.future.result(timeout=5)
        assert device.poll()
        assert device.diagnostics.local_db_status == "ok"
        assert device.diagnostics.installed_content_count == 1
        device.start("export")
        device.future.result(timeout=5)
        assert device.poll()
        bundles = list((tmp_path / "support").glob("*.zip"))
        assert len(bundles) == 1
        with zipfile.ZipFile(bundles[0]) as archive:
            assert not any(name.endswith(".db") for name in archive.namelist())
            content = archive.read("diagnostics.json").decode()
            assert "Local Student" not in content


def test_cached_catalog_adds_remote_chapters_without_hiding_local_sets(tmp_path):
    from datetime import UTC, datetime

    from app.content.catalog import RemotePack

    path = tmp_path / "catalog.db"
    with Repository(path) as repo:
        seed(repo)
        device = DeviceConsole(path)
        c = student(repo, device)
        local = repo.list_question_sets()[0]
        remote = RemotePack(
            local.id,
            2,
            local.title,
            local.subject,
            local.chapter,
            20,
            4096,
            "a" * 64,
            datetime.now(UTC),
        )
        device.catalog = (remote,)
        c.refresh_catalog()
        choose(c, "route", UIScreen.SUBJECTS)
        choose(c, "subject", 0)
        choose(c, "chapter", 0)
        assert "Downloaded" in c.choices[0].label
        assert "Update available" in c.choices[0].label
        assert c.choices[1].command == "download"
        device.download_state[(remote.set_id, remote.version)] = "VALIDATION_FAILED"
        assert "Validation failed" in c.choices[1].label
        choose(c, "pack", 0)
        choose(c, "start")
        assert c.screen is UIScreen.QUESTION
        c.close()


def test_navigator_can_jump_to_the_last_question(tmp_path):
    path = tmp_path / "large.db"
    with Repository(path) as repo:
        seed(repo)
        original = repo.list_question_sets()[0]
        questions = tuple(
            replace(original.questions[0], id=f"large-{index}", position=index + 1)
            for index in range(100)
        )
        repo.import_question_set(
            replace(original, id="large-set", questions=questions),
            content_hash="large",
            is_active=True,
        )
        c = student(repo)
        c.application.start_test(c.selected_profile.id, "large-set", 1)
        c.route(UIScreen.QUESTION)
        c.handle(Action.MENU)
        choose(c, "navigator")
        c.handle(Action.CONFIRM, ("question", 99))
        assert c.application.engine.current_index == 99
        c.close()


def test_pairing_cancel_invalidates_pending_result_and_keeps_local_profile(tmp_path):
    from concurrent.futures import Future
    from datetime import UTC, datetime, timedelta

    from app.auth.pairing import PairingRequest

    path = tmp_path / "pairing.db"
    with Repository(path) as repo:
        seed(repo)
        device = DeviceConsole(path, AppConfig(database_path=path, credential_path=tmp_path / "credential.json"))
        c = student(repo, device)
        choose(c, "route", UIScreen.SETTINGS)
        choose(c, "route", UIScreen.ACCOUNT)
        choose(c, "pair")
        assert c.screen is UIScreen.PAIRING
        pending = Future()
        device.operation, device.future = "pair_request", pending
        request = PairingRequest(
            "session", "123456", "never-display", datetime.now(UTC) + timedelta(minutes=5)
        )
        pending.set_result((device.generation, request))
        c.handle(Action.BACK)
        c.tick()
        assert device.pairing is None
        assert device.credentials.load_safe() is None
        assert c.screen is UIScreen.ACCOUNT
        assert repo.list_profiles()[0].display_name == "Local Student"


def test_wifi_adapter_passes_values_as_arguments_and_handles_escaped_ssids(monkeypatch):
    from types import SimpleNamespace

    from app.system.wifi import WifiService

    seen = []
    monkeypatch.setattr("app.system.wifi.shutil.which", lambda name: "nmcli")

    def command(arguments, **kwargs):
        seen.append((arguments, kwargs))
        return SimpleNamespace(returncode=0, stdout="")

    monkeypatch.setattr("app.system.wifi.subprocess.run", command)
    service = WifiService()
    service.connect("Campus; $(secret)", "pa$$word")
    arguments, options = seen[0]
    assert arguments[-3:] == ["Campus; $(secret)", "password", "pa$$word"]
    assert not options.get("shell")
    assert service._fields(r"School\:Lab:80:WPA2") == ["School:Lab", "80", "WPA2"]


def test_virtual_keyboard_modes_expose_allowed_characters(tmp_path):
    path = tmp_path / "keyboard.db"
    with Repository(path) as repo:
        c = UIController(repo, startup=True)
        c.finish_splash()
        c.route(UIScreen.ADD_PROFILE)
        for mode in range(3):
            c.keyboard_mode = mode
            chars = c.keyboard_characters
            assert chars
            for index in (0, len(chars) - 1):
                c.keyboard_index = index
                c.text_value = ""
                c.handle(Action.SELECT_A)
                assert c.text_value == chars[index]


def test_unconfigured_network_and_update_actions_are_clear_nonblocking_states(tmp_path):
    path = tmp_path / "unconfigured.db"
    with Repository(path) as repo:
        seed(repo)
        device = DeviceConsole(path)
        c = student(repo, device)
        choose(c, "route", UIScreen.SETTINGS)
        choose(c, "route", UIScreen.SOFTWARE_UPDATE)
        choose(c, "job", "update_check")
        assert "Server not configured" in c.message
        assert c.screen is UIScreen.SOFTWARE_UPDATE
        assert not device.busy
        c.handle(Action.BACK)
        c.handle(Action.BACK)
        begin(c)
        assert c.application.engine.state is AssessmentState.IN_QUESTION
        c.close()


def test_returning_account_refresh_does_not_interrupt_an_assessment(tmp_path):
    from concurrent.futures import Future
    from uuid import uuid4

    path = tmp_path / "background-account.db"
    with Repository(path) as repo:
        seed(repo)
        repo.cache_student_account_context(str(uuid4()), "Student")
        device = DeviceConsole(path, AppConfig(database_path=path))
        c = student(repo, device)
        begin(c)
        question_id = c.application.current_question().id
        device.operation = "account_sync"
        device.future = Future()
        device.future.set_result((device.generation, {}))
        c.tick()
        assert c.screen is UIScreen.QUESTION
        assert c.application.current_question().id == question_id
        assert repo.find_in_progress_attempt("test-profile") is not None
