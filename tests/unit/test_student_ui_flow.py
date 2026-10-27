"""Document-defined device flow against the real engine and file-backed repository."""

import hashlib
from dataclasses import replace
from pathlib import Path

import pygame
import pytest

from app.auth.credentials import CredentialStore
from app.auth.pin import PinUnlock
from app.config import AppConfig
from app.content.importer import import_pack
from app.core.engine import AssessmentState
from app.core.models import Confidence, Profile
from app.data.repo import Repository
from app.input.actions import Action
from app.input.ui import keyboard_input
from app.ui.app import run
from app.ui.components import detail_pages, full_content
from app.ui.controller import UIController
from app.ui.device import DeviceConsole
from app.ui.layout import LOGICAL_HEIGHT, LOGICAL_WIDTH
from app.ui.router import SETTINGS_ROUTES, UIScreen
from app.ui.screens import console, recovery, startup
from app.ui.screens.common import make_fonts
from app.ui.startup import StartupSession


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


def assert_fit(controls):
    for control in controls:
        rect = control.rect
        assert min(rect.width, rect.height) >= 48, control
        assert 0 <= rect.x <= LOGICAL_WIDTH - rect.width, control
        assert 0 <= rect.y <= LOGICAL_HEIGHT - rect.height, control


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
        assert controller.network_label == "Offline"


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


def test_pause_menu_home_confirmation_and_navigator_touch(tmp_path):
    pygame.font.init()
    surface, fonts = pygame.Surface((800, 480)), make_fonts()
    with Repository(tmp_path / "menu.db") as repo:
        seed(repo)
        c = student(repo)
        begin(c)
        c.handle(Action.MENU)
        assert c.screen is UIScreen.ASSESSMENT_MENU
        choose(c, "navigator")
        controls = console.render(surface, c, fonts)
        assert_fit(controls)
        control = next(control for control in controls if control.payload == ("question", 12))
        c.handle(control.action, control.payload)
        assert c.application.engine.current_index == 12
        c.handle(Action.PREV)
        assert c.application.engine.current_index == 11
        c.handle(Action.MENU)
        choose(c, "route", UIScreen.LEAVE_CONFIRM)
        assert c.screen is UIScreen.LEAVE_CONFIRM
        choose(c, "leave")
        assert c.screen is UIScreen.HOME
        assert c.can_resume


def test_empty_profile_requires_explicit_creation_and_supports_text_adapter(tmp_path):
    with Repository(tmp_path / "profiles.db") as repo:
        c = UIController(repo, startup=True)
        c.finish_splash()
        assert not c.profiles
        choose(c, "route", UIScreen.ADD_PROFILE)
        for char in "Riya":
            message = keyboard_input(char.lower(), character=char, text_entry=True)
            c.handle(message.action, message.payload)
        message = keyboard_input("return", text_entry=True)
        c.handle(message.action, message.payload)
        assert c.screen is UIScreen.HOME
        assert repo.list_profiles()[0].display_name == "Riya"


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
def test_every_settings_route_renders_offline_and_returns(tmp_path, route):
    pygame.font.init()
    fonts, surface = make_fonts(), pygame.Surface((800, 480))
    path = tmp_path / "settings.db"
    with Repository(path) as repo:
        seed(repo)
        device = DeviceConsole(path)
        c = student(repo, device)
        choose(c, "route", UIScreen.SETTINGS)
        choose(c, "route", route)
        assert c.screen is route
        assert_fit(console.render(surface, c, fonts))
        c.handle(Action.BACK)
        assert c.screen is UIScreen.SETTINGS


def test_real_startup_and_corrupt_database_recovery(tmp_path):
    pygame.font.init()
    fonts, surface = make_fonts(), pygame.Surface((800, 480))
    path = tmp_path / "startup.db"
    session = StartupSession(
        path, AppConfig(database_path=path), CredentialStore(tmp_path / "credential.json")
    )
    while not session.complete and not session.failed:
        startup.render(surface, session, fonts)
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
    for mode in ("recovery", "diagnostics", "options"):
        assert_fit(recovery.render(surface, session, fonts, mode=mode))
    session.close()


def test_long_question_options_and_explanation_have_unbounded_pages(tmp_path):
    pygame.font.init()
    surface, fonts = pygame.Surface((800, 480)), make_fonts()
    with Repository(tmp_path / "long.db") as repo:
        seed(repo)
        original = repo.list_question_sets()[0]
        q = replace(
            original.questions[0],
            question_text="Long question content. " * 120,
            options=tuple(
                replace(o, text=f"{o.key} long answer. " * 90)
                for o in original.questions[0].options
            ),
            explanation="Detailed explanation. " * 180,
        )
        repo.import_question_set(
            replace(original, version=2, questions=(q,)), content_hash="long", is_active=True
        )
        c = student(repo)
        begin(c)
        # Choose the long immutable version explicitly.
        c.application.abandon()
        c.application = c._application_factory(repo)
        c.application.start_test(c.selected_profile.id, original.id, 2)
        c.route(UIScreen.QUESTION)
        assert_fit(console.render(surface, c, fonts))
        c.handle(Action.CONFIRM)
        assert c.screen is UIScreen.QUESTION_DETAIL
        rendered_lines = []
        rendered_lines.extend(detail_pages(c, fonts))
        count = c.page_count
        assert count > 3
        for _ in range(count - 1):
            c.handle(Action.NEXT)
            rendered_lines.extend(detail_pages(c, fonts))
            assert_fit(console.render(surface, c, fonts))
        assert " ".join(full_content(c).split()) == " ".join(" ".join(rendered_lines).split())
        c.handle(Action.BACK)
        c.handle(Action.SELECT_A)
        c.handle(Action.SURE)
        c.handle(Action.SUBMIT)
        c.handle(Action.SUBMIT)
        choose(c, "review", "all")
        assert_fit(console.render(surface, c, fonts))
        c.handle(Action.CONFIRM)
        detail_pages(c, fonts)
        assert c.page_count > count


def test_entry_point_real_boot_headless_and_recovery(tmp_path, monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    path = tmp_path / "app.db"
    config = AppConfig(database_path=path, log_directory=tmp_path / "logs")
    assert run(path, config=config, max_frames=16) == 0
    bad = tmp_path / "bad.db"
    bad.write_bytes(b"bad database")
    assert run(bad, config=replace(config, database_path=bad), max_frames=8) == 1


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


def test_navigator_paginates_large_sets_and_touch_targets_fit(tmp_path):
    pygame.font.init()
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
        for _ in range(99):
            c.handle(Action.NEXT)
        controls = console.render(pygame.Surface((800, 480)), c, make_fonts())
        assert_fit(controls)
        assert any(control.payload == ("question", 99) for control in controls)
        c.handle(Action.SELECT_A)
        assert c.application.engine.current_index == 99
        c.close()


def test_pairing_cancel_invalidates_pending_result_and_keeps_local_profile(tmp_path):
    from concurrent.futures import Future
    from datetime import UTC, datetime, timedelta

    from app.auth.pairing import PairingRequest

    path = tmp_path / "pairing.db"
    with Repository(path) as repo:
        seed(repo)
        device = DeviceConsole(path)
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


def test_all_virtual_keyboard_targets_fit_and_every_character_is_reachable(tmp_path):
    pygame.font.init()
    path = tmp_path / "keyboard.db"
    with Repository(path) as repo:
        c = UIController(repo, startup=True)
        c.finish_splash()
        choose(c, "route", UIScreen.ADD_PROFILE)
        surface, fonts = pygame.Surface((800, 480)), make_fonts()
        for mode in range(3):
            c.keyboard_mode = mode
            chars = c.keyboard_characters
            for index in (0, len(chars) - 1):
                c.keyboard_index = index
                controls = console.render(surface, c, fonts)
                assert_fit(controls)
                assert any(control.payload == ("text", chars[index]) for control in controls)


def test_virtual_keyboard_more_keys_is_reachable_by_touch(tmp_path):
    pygame.font.init()
    with Repository(tmp_path / "more-keys.db") as repo:
        c = UIController(repo, startup=True)
        c.finish_splash()
        choose(c, "route", UIScreen.ADD_PROFILE)
        c.keyboard_mode = 2
        surface, fonts = pygame.Surface((800, 480)), make_fonts()
        controls = console.render(surface, c, fonts)
        if len(c.keyboard_characters) > 40:
            more = next(
                control for control in controls if control.payload == ("command", "more_keys")
            )
            c.handle(more.action, more.payload)
            controls = console.render(surface, c, fonts)
            last = c.keyboard_characters[-1]
            key = next(control for control in controls if control.payload == ("text", last))
            c.handle(key.action, key.payload)
            assert c.text_value == last


def test_entry_point_does_not_require_writable_log_storage(tmp_path, monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    blocked = tmp_path / "blocked-logs"
    blocked.write_text("Existing file; this cannot be a log directory")
    path = tmp_path / "log-test.db"
    assert (
        run(path, config=AppConfig(database_path=path, log_directory=blocked), max_frames=16) == 0
    )
    with Repository(path) as repo:
        assert repo.quick_check().ok


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
