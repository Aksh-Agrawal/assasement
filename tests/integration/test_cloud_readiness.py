"""Device-only wire integration; no server source or public host is required."""

import httpx
import pytest

from app.api.client import DeviceApi
from app.api.transport import FailureState, failure_state
from app.auth.credentials import CredentialStore, DeviceCredential
from app.config import AppConfig
from app.content.catalog import ContentCatalog
from app.content.importer import import_pack
from app.content.sync import ContentSyncStatus, sync_content_once
from app.data.repo import Repository
from tests.content.test_content_sync import pack_bytes, remote
from tools.cloud_check import check


def test_pair_claim_persists_and_authenticates_after_restart(tmp_path):
    config = AppConfig(api_base_url="https://device.test",
                       credential_path=tmp_path / "credential.json")
    requests = []

    def server(request):
        requests.append(request)
        if request.url.path.endswith("request"):
            return httpx.Response(201, json={"session_id": "session", "pairing_code": "123456",
                "claim_secret": "claim-canary", "expires_at": "2099-01-01T00:00:00Z"})
        if request.url.path.endswith("status"):
            assert request.headers["X-Pairing-Claim"] == "claim-canary"
            return httpx.Response(200, json={"status": "approved"})
        if request.url.path.endswith("claim"):
            return httpx.Response(200, json={"credential": "token-canary"})
        assert request.headers["Authorization"] == "Bearer token-canary"
        return httpx.Response(200, json={"schema_version": 1, "packs": [], "future": True})

    transport = httpx.MockTransport(server)
    api = DeviceApi(config, transport=transport)
    with api.pairing() as client:
        pairing = client.request("device")
        assert "claim-canary" not in repr(pairing)
        client.wait_and_claim(pairing, api.store, "device")
    restarted = DeviceApi(config, transport=transport)
    assert "token-canary" not in repr(restarted.store.load())
    with restarted.content() as client:
        assert client.fetch_catalog().packs == ()
    assert len(requests) == 4


@pytest.mark.parametrize("mode, expected", [
    ("timeout", FailureState.TIMEOUT), ("offline", FailureState.OFFLINE),
    (401, FailureState.AUTH_REQUIRED), (500, FailureState.SERVER_ERROR),
    ("invalid", FailureState.INVALID_RESPONSE),
])
def test_cloud_check_safe_failure_states(tmp_path, mode, expected):
    config = AppConfig(api_base_url="https://device.test", credential_path=tmp_path / "creds")
    CredentialStore(config.credential_path).save(DeviceCredential("device", "token-canary"))

    def server(request):
        if mode == "timeout":
            raise httpx.ReadTimeout("secret-canary", request=request)
        if mode == "offline":
            raise httpx.ConnectError("secret-canary", request=request)
        if mode == "invalid":
            return httpx.Response(200, text="invalid")
        return httpx.Response(mode, json={})

    result = check(config, transport=httpx.MockTransport(server))
    assert result["Cloud readiness"] == expected.value
    assert "canary" not in repr(result)


def test_unconfigured_cloud_check_does_no_io(tmp_path):
    assert check(AppConfig(api_base_url=None, credential_path=tmp_path / "absent")) == {
        "API configured": "NO", "Cloud readiness": "WAITING_FOR_API_URL"}
    assert not list(tmp_path.iterdir())


def test_catalog_compatible_extra_fields():
    entry = {**remote(pack_bytes()), "future": {"optional": True}}
    assert ContentCatalog.from_dict({"schema_version": 1, "packs": [entry], "future": 1}).packs


def test_interrupted_stream_retains_installed_content_and_can_retry(tmp_path):
    old = tmp_path / "old.json"
    old.write_bytes(pack_bytes())
    new = pack_bytes(2, changed=True)

    class BrokenStream(httpx.SyncByteStream):
        def __iter__(self):
            yield new[:100]
            raise httpx.ReadError("network lost")

    broken = True

    def server(request):
        if request.url.path.endswith("catalog"):
            return httpx.Response(200, json={"schema_version": 1, "packs": [remote(new, 2)]})
        return httpx.Response(200, stream=BrokenStream()) if broken else httpx.Response(200, content=new)

    config = AppConfig(api_base_url="https://device.test", credential_path=tmp_path / "creds")
    CredentialStore(config.credential_path).save(DeviceCredential("device", "token"))
    with Repository(tmp_path / "device.db") as repo:
        import_pack(old, repo)
        with DeviceApi(config, transport=httpx.MockTransport(server)).content() as client:
            def sync():
                return sync_content_once(repo, client, temp_directory=tmp_path / "downloads",
                                         max_pack_bytes=1000000, max_downloads_per_cycle=1)

            assert sync().packs[0].status is ContentSyncStatus.NETWORK_UNAVAILABLE
            assert repo.get_active_question_set("biology-cell-practice-01").version == 1
            assert not list((tmp_path / "downloads").iterdir())
            broken = False
            assert sync().packs[0].status is ContentSyncStatus.INSTALLED
            assert repo.get_question_set("biology-cell-practice-01", 1) is not None


def test_wrapped_transport_failure_retains_type():
    try:
        try:
            raise httpx.ReadTimeout("private transport detail")
        except httpx.ReadTimeout as error:
            raise RuntimeError("safe wrapper") from error
    except RuntimeError as error:
        assert failure_state(error) is FailureState.TIMEOUT


def test_verified_transport_is_mandatory(monkeypatch):
    from app.api import transport

    received = {}

    def client(**kwargs):
        received.update(kwargs)
        return object()

    monkeypatch.setattr(transport.httpx, "Client", client)
    transport.create_client("https://device.test", auth_token="token", connect_timeout=2,
                            read_timeout=7)
    assert received["verify"] is True
    assert received["follow_redirects"] is False
    assert received["timeout"].connect == 2
    assert received["timeout"].read == 7


def test_catalogue_server_failure_is_distinct_from_offline(tmp_path):
    from app.content.client import ContentApiClient, ContentNetworkError

    with ContentApiClient("https://device.test", auth_token="token",
                          transport=httpx.MockTransport(lambda request: httpx.Response(500))) as client:
        with pytest.raises(ContentNetworkError) as caught:
            client.fetch_catalog()
    assert failure_state(caught.value) is FailureState.SERVER_ERROR


def test_heartbeat_failure_does_not_hide_upload_result_or_stop_metadata(tmp_path, monkeypatch):
    from app.sync import service

    config = AppConfig(api_base_url="https://device.test", database_path=tmp_path / "device.db",
                       credential_path=tmp_path / "creds")
    CredentialStore(config.credential_path).save(DeviceCredential("device", "token"))
    paths = []

    def server(request):
        paths.append(request.url.path)
        if request.url.path.endswith("heartbeat"):
            return httpx.Response(503)
        if request.url.path.endswith("catalog"):
            return httpx.Response(200, json={"schema_version": 1, "packs": []})
        return httpx.Response(404)

    monkeypatch.setattr(service, "DeviceApi", lambda config: DeviceApi(
        config, transport=httpx.MockTransport(server)))
    result = service.run_cycle(config, refresh=True)
    assert result.selected == 0
    assert paths == ["/api/v1/devices/heartbeat", "/api/v1/content/catalog",
                     "/api/v1/device-updates/latest"]
    with Repository(config.database_path) as repo:
        assert repo.get_setting("last_heartbeat_state") == "HTTPStatusError"
        assert repo.get_setting("last_catalogue_check") == "OK"


def test_failed_credential_replace_preserves_previous_token(tmp_path, monkeypatch):
    from pathlib import Path

    store = CredentialStore(tmp_path / "creds")
    store.save(DeviceCredential("device", "previous"))

    def fail(*args):
        raise OSError("simulated storage interruption")

    monkeypatch.setattr(Path, "replace", fail)
    with pytest.raises(OSError):
        store.save(DeviceCredential("device", "replacement"))
    assert store.load().token == "previous"
    assert list(tmp_path.iterdir()) == [store.path]

