import httpx
import pytest

from app.api.client import DeviceApi
from app.auth.credentials import CredentialStore, DeviceCredential
from app.config import AppConfig
from app.connectivity import cloud_label, cloud_state, record_probe, sync_label
from app.content.client import ContentClientError
from app.data.repo import Repository
from app.diagnostics import NetworkStatus


def api_for(tmp_path, handler):
    config = AppConfig(api_base_url="https://cloud.test", database_path=tmp_path / "pi.db",
                       credential_path=tmp_path / "credentials.json")
    store = CredentialStore(config.credential_path)
    store.save(DeviceCredential("device", "secret"))
    return DeviceApi(config, store=store, transport=httpx.MockTransport(handler))


def test_authenticated_catalogue_and_content_contact_updates_shared_state(tmp_path):
    from pathlib import Path

    from app.content.catalog import RemotePack
    from tests.content.test_profile_library import metadata

    data = Path("content/sample_biology.json").read_bytes()
    item = metadata(data)
    def handler(request):
        if request.url.path.endswith("catalog"):
            return httpx.Response(200, json={"schema_version": 1, "packs": [item]})
        return httpx.Response(200, content=data)
    api = api_for(tmp_path, handler)
    with Repository(api.config.database_path) as repo:
        assert cloud_label(repo) == "Checking…"
        with api.content() as client:
            client.fetch_catalog()
        assert cloud_label(repo) == "Online"
        first = cloud_state(repo)["last_cloud_success"]
        with api.content() as client:
            # Exercise the same observed transport used by the streaming download path.
            with client.stream_pack(RemotePack.from_dict(item)) as response:
                assert response.read() == data
        assert cloud_state(repo)["last_cloud_success"] >= first
        assert "secret" not in repo.get_setting("connectivity_cloud")
        assert sync_label(repo) == "Up to date"


@pytest.mark.parametrize("code, expected", [(401, "Authentication required"),
    (403, "Authentication required"), (503, "Server unavailable")])
def test_authenticated_failures_update_cloud_state(tmp_path, code, expected):
    api = api_for(tmp_path, lambda request: httpx.Response(code))
    with Repository(api.config.database_path) as repo:
        with api.content() as client, pytest.raises(ContentClientError):
            client.fetch_catalog()
        assert cloud_label(repo) == expected


def test_unreachable_cloud_is_offline(tmp_path):
    def handler(request):
        raise httpx.ConnectError("unreachable", request=request)
    api = api_for(tmp_path, handler)
    with Repository(api.config.database_path) as repo:
        with api.content() as client, pytest.raises(ContentClientError):
            client.fetch_catalog()
        assert cloud_label(repo) == "Offline"


def test_ready_failure_is_server_unavailable_and_does_not_change_internet(tmp_path):
    with Repository(tmp_path / "pi.db") as repo:
        record_probe(repo.database_path, NetworkStatus(checked=True, backend_reachable=True,
                                                      database_ready=False))
        assert cloud_label(repo) == "Server unavailable"
        record_probe(repo.database_path, NetworkStatus(checked=True, backend_reachable=False))
        assert cloud_label(repo) == "Offline"


def test_successful_empty_sync_has_cloud_contact_and_sync_success(tmp_path, monkeypatch):
    from app.sync import service

    api = api_for(tmp_path, lambda request: httpx.Response(200, json={"status": "accepted"}))
    monkeypatch.setattr(service, "DeviceApi", lambda config: api)
    with Repository(api.config.database_path) as repo:
        result = service.run_cycle(api.config, heartbeat=True)
        assert result.selected == 0
        assert cloud_label(repo) == "Online"
        assert sync_label(repo) == "Up to date"
        assert repo.get_setting("last_sync_success")


def test_profile_sync_is_authenticated_cloud_evidence(tmp_path):
    from uuid import uuid4

    from app.auth.account_device import sync_account

    api = api_for(tmp_path, lambda request: httpx.Response(200))
    with Repository(api.config.database_path) as repo:
        response = {"account_id": str(uuid4()), "display_name": "Account", "profiles": []}
        sync_account(api.config, api.store, repo, transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=response)))
        assert cloud_label(repo) == "Online"
        assert cloud_state(repo)["last_cloud_success"]
