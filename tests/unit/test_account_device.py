from uuid import uuid4

import httpx
import pytest

from app.auth.account_device import sync_account
from app.auth.credentials import CredentialStore, DeviceCredential
from app.config import AppConfig
from app.core.models import Profile
from app.data.repo import Repository
from app.ui.controller import UIController
from app.ui.router import UIScreen


def test_account_sync_legacy_preservation_cached_restart_rename_limit_and_revoke(tmp_path):
    account, pid, link = str(uuid4()), str(uuid4()), str(uuid4())
    data = {
        "account_id": account,
        "display_name": "Aksh",
        "profile_count": 1,
        "profile_limit": 3,
        "profiles": [
            {
                "id": pid,
                "account_id": account,
                "local_profile_id": "cloud-" + pid,
                "link_id": link,
                "name": "NEET",
                "exam_context": "NEET",
            }
        ],
    }
    store = CredentialStore(tmp_path / "credentials.json")
    store.save(DeviceCredential(str(uuid4()), "device_test.secret"))
    config = AppConfig(api_base_url="https://example.test")

    def handler(request):
        assert request.headers["Authorization"] == "Bearer device_test.secret"
        return httpx.Response(200, json=data)

    path = tmp_path / "device.db"
    with Repository(path) as repo:
        repo.create_profile(Profile("legacy", "Legacy"))
        sync_account(config, store, repo, transport=httpx.MockTransport(handler))
        assert repo.get_profile("legacy").ownership_state == "legacy_unclaimed"
        c = UIController(repo, startup=True)
        c.finish_splash()
        assert c.screen is UIScreen.PROFILE and len(c.profiles) == 1
        assert c.profiles[0].display_name == "NEET"
        assert any(ch.label == "+ Create Profile" for ch in c.choices)
        assert not any(
            ch.label in {"Development", "Add local profile", "Add / Pair device"}
            for ch in c.choices
        )
        data["profiles"][0]["name"] = "NEET updated"
        sync_account(config, store, repo, transport=httpx.MockTransport(handler))
        assert repo.get_profile("cloud-" + pid).display_name == "NEET updated"
        data["profile_count"] = 3
        sync_account(config, store, repo, transport=httpx.MockTransport(handler))
        c.refresh_catalog()
        assert not any("Create" in ch.label for ch in c.choices)
    with Repository(path) as repo:
        c = UIController(repo, startup=True)
        c.finish_splash()
        assert c.screen is UIScreen.PROFILE and len(c.profiles) == 1

        def offline(request):
            raise httpx.ConnectError("offline", request=request)

        with pytest.raises(httpx.RequestError):
            sync_account(config, store, repo, transport=httpx.MockTransport(offline))
        assert repo.get_student_account_context()["cloud_account_id"] == account
        with pytest.raises(httpx.HTTPStatusError):
            sync_account(
                config,
                store,
                repo,
                transport=httpx.MockTransport(lambda request: httpx.Response(403)),
            )
        assert repo.get_student_account_context() is None
        assert len(repo.list_profiles()) == 2


def test_cloud_create_never_creates_local_anonymous_profile_on_failure(tmp_path):
    store = CredentialStore(tmp_path / "credentials.json")
    store.save(DeviceCredential(str(uuid4()), "device_test.secret"))
    with Repository(tmp_path / "device.db") as repo:
        with pytest.raises(httpx.HTTPStatusError):
            sync_account(
                AppConfig(api_base_url="https://example.test"),
                store,
                repo,
                create={"name": "fourth", "exam_context": "x"},
                transport=httpx.MockTransport(lambda request: httpx.Response(409)),
            )
        assert repo.list_profiles() == ()


def test_account_labels_require_fresh_verification_and_explain_revocation(tmp_path):
    from datetime import UTC, datetime, timedelta

    from app.auth.product_state import account_status
    now = datetime.now(UTC)
    with Repository(tmp_path / "status.db") as repo:
        assert account_status(repo) == "Not connected"
        repo.cache_student_account_context(str(uuid4()), "Student", last_verified_at=now)
        repo.set_setting("account_connection_state", "connected")
        assert account_status(repo) != "Connected"  # Restart cache alone proves nothing.
        assert account_status(repo, verified_this_run=True, now=now) == "Connected"
        assert account_status(repo, verified_this_run=True, now=now + timedelta(seconds=180)) != "Connected"
        assert account_status(repo, busy=True) == "Verifying"
        repo.set_setting("account_connection_state", "offline_cached")
        assert account_status(repo).startswith("Offline - last verified")
        repo.set_setting("account_connection_state", "revoked")
        assert account_status(repo) == "Reconnection required"


def test_account_sync_hides_archived_profiles_without_removing_cached_records(tmp_path):
    account, pid, lid = str(uuid4()), str(uuid4()), str(uuid4())
    data = {"account_id": account, "display_name": "Student", "profile_count": 1,
            "profiles": [{"id": pid, "account_id": account, "name": "NEET",
                          "local_profile_id": "cloud-" + pid, "link_id": lid}]}
    store = CredentialStore(tmp_path / "credentials.json")
    store.save(DeviceCredential(str(uuid4()), "device_test.secret"))
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=data))
    with Repository(tmp_path / "archive.db") as repo:
        config = AppConfig(api_base_url="https://example.test")
        sync_account(config, store, repo, transport=transport)
        data["profiles"] = []
        data["profile_count"] = 0
        sync_account(config, store, repo, transport=transport)
        controller = UIController(repo, startup=True)
        controller.finish_splash()
        assert controller.profiles == ()
        assert repo.get_profile("cloud-" + pid) is not None
