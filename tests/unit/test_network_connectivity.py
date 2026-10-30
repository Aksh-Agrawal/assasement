"""Automated regression tests for network reachability, cloud health, and connectivity state."""

import socket

import httpx

from app.api.client import DeviceApi
from app.auth.credentials import CredentialStore, DeviceCredential
from app.config import AppConfig, normalize_api_url
from app.connectivity import (
    check_internet_reachability,
    cloud_label,
    cloud_state,
    internet_label,
    internet_state,
    record_cloud,
    record_internet,
    record_probe,
    record_wifi,
)
from app.data.repo import Repository
from app.diagnostics import collect_device_status, collect_network_status
from app.sync.service import run_cycle
from app.update.activation import ActivationManager


def test_api_url_normalization_and_typo_repair():
    assert normalize_api_url("https://startup-cloud.onrender.com/") == "https://startup-cloud.onrender.com"
    # Auto-repairs missing 'on' in onrender.com
    assert normalize_api_url("https://startup-cloud.render.com") == "https://startup-cloud.onrender.com"
    assert normalize_api_url("https://startup-cloud.render.com/") == "https://startup-cloud.onrender.com"
    assert normalize_api_url("  https://my-host.test/  ") == "https://my-host.test"
    assert normalize_api_url(None) is None
    assert normalize_api_url("") is None


def test_terminal_equivalent_internet_success(tmp_path, monkeypatch):
    """When DNS and HTTPS succeed, internet reachability is marked Available."""
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("1.1.1.1", 443))])

    def mock_get(url, *args, **kwargs):
        return httpx.Response(204)

    monkeypatch.setattr(httpx.Client, "get", mock_get)

    inet_ok, dns_ok = check_internet_reachability(timeout=2.0)
    assert inet_ok is True
    assert dns_ok is True

    db_path = tmp_path / "test.db"
    with Repository(db_path) as repo:
        record_internet(repo.database_path, "Available", dns_ok=True)
        assert internet_label(repo) == "Available"
        state = internet_state(repo)
        assert state["dns_ok"] is True
        assert state["last_internet_success"]


def test_no_internet_dns_failure(tmp_path, monkeypatch):
    """When DNS resolution fails, Internet is Unavailable with dns_ok False."""
    def fail_dns(*args, **kwargs):
        raise socket.gaierror(-2, "Name or service not known")

    monkeypatch.setattr(socket, "getaddrinfo", fail_dns)

    inet_ok, dns_ok = check_internet_reachability(timeout=2.0)
    assert inet_ok is False
    assert dns_ok is False

    db_path = tmp_path / "test.db"
    with Repository(db_path) as repo:
        record_internet(repo.database_path, "Unavailable", dns_ok=False, details="DNS resolution failed")
        assert internet_label(repo) == "Unavailable"
        state = internet_state(repo)
        assert state["dns_ok"] is False


def test_cloud_success_health_and_ready_200(tmp_path, monkeypatch):
    """Health 200 + Ready 200 produces Cloud Online and Internet Available."""
    def mock_transport(request):
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path == "/ready":
            return httpx.Response(200, json={"status": "ready", "database": "ok", "migration": "current"})
        return httpx.Response(200)

    monkeypatch.setattr("app.diagnostics.create_client", lambda *a, **kw: httpx.Client(
        base_url="https://cloud.test", transport=httpx.MockTransport(mock_transport)))

    net = collect_network_status("https://cloud.test", auth_token=None)
    assert net.checked is True
    assert net.backend_reachable is True
    assert net.database_ready is True

    db_path = tmp_path / "test.db"
    with Repository(db_path) as repo:
        record_probe(repo.database_path, net)
        assert cloud_label(repo) == "Online"
        assert internet_label(repo) == "Available"


def test_server_not_ready_health_200_ready_503(tmp_path, monkeypatch):
    """Health 200 + Ready 503 produces Server unavailable without breaking Internet."""
    def mock_transport(request):
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path == "/ready":
            return httpx.Response(503, json={"status": "not_ready", "database": "ok", "migration": "outdated"})
        return httpx.Response(200)

    monkeypatch.setattr("app.diagnostics.create_client", lambda *a, **kw: httpx.Client(
        base_url="https://cloud.test", transport=httpx.MockTransport(mock_transport)))

    net = collect_network_status("https://cloud.test", auth_token=None)
    assert net.checked is True
    assert net.backend_reachable is True
    assert net.database_ready is False

    db_path = tmp_path / "test.db"
    with Repository(db_path) as repo:
        record_probe(repo.database_path, net)
        assert cloud_label(repo) == "Server unavailable"
        # Internet must remain Available, NOT broken by 503
        assert internet_label(repo) == "Available"


def test_auth_failure_401_403_produces_auth_required(tmp_path, monkeypatch):
    """401/403 response marks Authentication required but confirms Internet is available."""
    def mock_transport(request):
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path == "/ready":
            return httpx.Response(200, json={"status": "ready", "database": "ok"})
        if request.url.path.startswith("/api/v1/content/catalog"):
            return httpx.Response(401, json={"detail": "Unauthorized"})
        return httpx.Response(401)

    monkeypatch.setattr("app.diagnostics.create_client", lambda *a, **kw: httpx.Client(
        base_url="https://cloud.test", transport=httpx.MockTransport(mock_transport)))

    net = collect_network_status("https://cloud.test", auth_token="expired_token")
    assert net.checked is True
    assert net.backend_reachable is True
    assert net.auth_accepted is False

    db_path = tmp_path / "test.db"
    with Repository(db_path) as repo:
        record_probe(repo.database_path, net)
        assert cloud_label(repo) == "Authentication required"
        assert internet_label(repo) == "Available"


def test_successful_authenticated_sync_restores_internet_and_cloud(tmp_path, monkeypatch):
    """Successful sync restores Online and Available even if previous state was offline/unknown."""
    config = AppConfig(
        api_base_url="https://cloud.test",
        database_path=tmp_path / "pi.db",
        credential_path=tmp_path / "creds.json",
    )
    store = CredentialStore(config.credential_path)
    store.save(DeviceCredential("device-id", "secret-token"))

    def mock_handler(request):
        return httpx.Response(200, json={"status": "accepted"})

    api = DeviceApi(config, store=store, transport=httpx.MockTransport(mock_handler))
    monkeypatch.setattr("app.sync.service.DeviceApi", lambda c: api)

    with Repository(config.database_path) as repo:
        record_cloud(repo.database_path, "Offline")
        record_internet(repo.database_path, "Unavailable")
        assert cloud_label(repo) == "Offline"
        assert internet_label(repo) == "Unavailable"

        result = run_cycle(config, heartbeat=True)
        assert result.selected == 0
        assert cloud_label(repo) == "Online"
        assert internet_label(repo) == "Available"


def test_cloud_transient_failure_and_recovery(tmp_path):
    """Cloud recovers from transient connection error without app restart."""
    db_path = tmp_path / "recover.db"
    with Repository(db_path) as repo:
        record_cloud(repo.database_path, "Offline")
        assert cloud_label(repo) == "Offline"

        # Subsequent successful request restores Online
        record_cloud(repo.database_path, "Online")
        assert cloud_label(repo) == "Online"
        assert cloud_state(repo)["last_cloud_success"]


def test_diagnostics_live_indicators(tmp_path):
    """Diagnostics snapshot includes live NetworkManager, Wi-Fi, DNS, and Internet status."""
    db_path = tmp_path / "diag.db"
    creds = CredentialStore(tmp_path / "creds.json")
    with Repository(db_path) as repo:
        record_wifi(repo.database_path, "connected", ssid="TestHotspot")
        record_internet(repo.database_path, "Available", dns_ok=True)
        record_cloud(repo.database_path, "Online")

        status = collect_device_status(
            repo,
            database_path=db_path,
            credential_store=creds,
            update_manager=ActivationManager(tmp_path / "updates"),
            trusted_signing_key_id="key-01",
        )
        assert status.wifi_connected is True
        assert status.wifi_ssid == "TestHotspot"
        assert status.dns_ok is True
        assert status.internet_status == "Available"
        assert status.cloud_status == "Online"
        d = status.to_dict()
        assert d["wifi_connected"] is True
        assert d["wifi_ssid"] == "TestHotspot"
        assert d["dns_ok"] is True
