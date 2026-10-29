from pathlib import Path
from uuid import uuid4

import httpx
import pygame
import pytest

from app.assessment import AssessmentApplication
from app.auth.credentials import CredentialStore, DeviceCredential
from app.auth.profile_links import ProfileLinkClient, ProfileLinkError
from app.config import AppConfig
from app.content.importer import import_pack
from app.core.models import Profile
from app.data.repo import Repository
from app.input.actions import Action
from app.ui.controller import UIController
from app.ui.device import DeviceConsole
from app.ui.router import UIScreen
from app.ui.screens import console
from app.ui.screens.common import make_fonts


def result(local="p1"):
    return {"status": "linked", "link_id": str(uuid4()), "student_account_id": str(uuid4()),
            "study_profile_id": str(uuid4()), "account_display_name": "Student",
            "study_profile_name": "NEET", "local_profile_id": local}


def choose(c, command):
    i = next(i for i, choice in enumerate(c.choices) if choice.command == command)
    c.handle(Action.CONFIRM, ("choice", i))


def test_explicit_ui_code_confirmation_and_cancel(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSESS_MAINTENANCE", "1")
    pygame.font.init()
    with Repository(tmp_path / "db") as repo:
        repo.create_profile(Profile("p1", "NEET Practice"))
        c = UIController(repo, startup=True)
        c.finish_splash()
        choose(c, "profile")
        c.route(UIScreen.ACCOUNT)
        choose(c, "profile_link")
        assert c.screen is UIScreen.LINK_PROFILE
        c.handle_text("abcd efgh23")
        assert c.text_value == "ABCDEFGH23"
        surface, fonts = pygame.Surface((800, 480)), make_fonts()
        for control in console.render(surface, c, fonts):
            assert 0 <= control.rect.x <= 800 - control.rect.width
            assert 0 <= control.rect.y <= 480 - control.rect.height
        c.handle(Action.CONFIRM)
        assert c.screen is UIScreen.LINK_CONFIRM
        assert c.selected_profile.id == "p1"
        console.render(surface, c, fonts)
        c.handle(Action.BACK)
        assert c.screen is UIScreen.ACCOUNT and c.text_value == ""


@pytest.mark.parametrize("code", ["LINK_INVALID", "LINK_EXPIRED", "LINK_CONSUMED",
                                  "LINK_CANCELLED", "LINK_PROFILE_CONFLICT"])
def test_machine_errors_are_safe(code):
    def handler(request):
        return httpx.Response(409, json={"detail": {"code": code, "message": "private raw detail"}})
    with ProfileLinkClient("https://cloud.test", auth_token="technical",
                           transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ProfileLinkError) as error:
            client.claim("ABCDEFGH23", "p1")
        assert error.value.code == code
        assert "private" not in str(error.value)


def test_network_and_missing_credential_states():
    def offline(request):
        raise httpx.ConnectError("secret connection details", request=request)
    with ProfileLinkClient("https://cloud.test", auth_token="technical",
                           transport=httpx.MockTransport(offline)) as client:
        with pytest.raises(ProfileLinkError, match="Check your connection"):
            client.claim("ABCDEFGH23", "p1")
    with ProfileLinkClient("https://cloud.test") as client:
        with pytest.raises(ProfileLinkError, match="Device authentication required"):
            client.claim("ABCDEFGH23", "p1")


def test_selected_profile_persistence_and_attempt_snapshot(tmp_path):
    path = tmp_path / "db"
    linked = result()
    with Repository(path) as repo:
        repo.create_profile(Profile("p1", "Local"))
        repo.create_profile(Profile("p2", "Other"))
        import_pack(Path("content/sample_biology.json"), repo)
        app = AssessmentApplication(repo)
        legacy = app.start_test("p1", "biology-cell-practice-01", 1)
        app.pause()
        repo.apply_profile_link("p1", linked)
        assert repo.get_attempt_ownership(legacy.id) is None
        assert repo.get_profile("p2").ownership_state == "legacy_unclaimed"
        other = result()
        with pytest.raises(ValueError, match="overwritten"):
            repo.apply_profile_link("p1", other)
        # A new attempt on another explicitly linked local profile snapshots its link.
        linked2 = {**linked, "local_profile_id": "p2", "link_id": str(uuid4())}
        repo.apply_profile_link("p2", linked2)
        new = AssessmentApplication(repo).start_test("p2", "biology-cell-practice-01", 1)
        assert repo.get_attempt_ownership(new.id)["link_id"] == linked2["link_id"]
        repo.apply_profile_link("p2", {**linked2, "status": "revoked"})
        assert repo.get_profile("p2").link_state == "unlinked"
        assert repo.get_attempt_ownership(new.id)["link_id"] == linked2["link_id"]
    with Repository(path) as repo:
        assert repo.get_profile("p1").link_state == "linked"
        assert repo.get_profile_link_context("p1")["study_profile_name"] == "NEET"
        assert repo.get_attempt(legacy.id) is not None


def test_console_links_in_background_and_persists_exact_profile(tmp_path, monkeypatch):
    path = tmp_path / "db"
    store = CredentialStore(tmp_path / "credential.json")
    with Repository(path) as repo:
        store.save(DeviceCredential(repo.get_or_create_device_id(), "device_test.secret"))
        repo.create_profile(Profile("p1", "Local"))
        repo.create_profile(Profile("p2", "Other"))
        data = result()
        def client(self):
            return ProfileLinkClient("https://cloud.test", auth_token="technical",
                transport=httpx.MockTransport(lambda request: httpx.Response(200, json=data)))
        monkeypatch.setattr("app.api.client.DeviceApi.profile_links", client)
        d = DeviceConsole(path, AppConfig(database_path=path, api_base_url="https://cloud.test"),
                          credentials=store)
        d.start("profile_claim", code="ABCDEFGH23", local_profile_id="p1")
        d.future.result(timeout=5)
        assert d.poll()
        assert repo.get_profile("p1").link_state == "linked"
        assert repo.get_profile("p2").ownership_state == "legacy_unclaimed"
        d.start("profile_claim", code="ABCDEFGH23", local_profile_id="p1")
        with pytest.raises(ProfileLinkError):
            d.future.result(timeout=5)
        d.poll()
        assert d.message == "Profile already linked"
