"""Regression coverage for an independently installable offline device."""

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from app.api.client import DeviceApi
from app.api.heartbeat import Heartbeat, HeartbeatClient
from app.auth.pairing import PairingClient
from app.config import AppConfig
from app.content.client import ContentApiClient
from app.sync.client import SyncApiClient
from app.sync.errors import TransientSyncError
from app.sync.service import run_cycle


def test_device_imports_and_assessment_without_cloud(tmp_path):
    # Import hook fails even when backend/server packages exist in the developer environment.
    script = """
import importlib.abc
import pkgutil
import sys
class NoCloud(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'backend', 'fastapi', 'sqlalchemy', 'psycopg', 'alembic'}:
            raise AssertionError('Cloud import attempted: ' + fullname)
sys.meta_path.insert(0, NoCloud())
import app
for item in pkgutil.walk_packages(app.__path__, 'app.'):
    try:
        __import__(item.name)
    except ModuleNotFoundError as error:
        if error.name != "pygame":
            raise
from tools.pilot_check import smoke_assessment
assert smoke_assessment()
"""
    environment = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, env=environment
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_config_environment_and_explicit_overrides(monkeypatch, tmp_path):
    monkeypatch.setenv("ASSESS_API_URL", "https://configured.invalid")
    monkeypatch.setenv("ASSESS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ASSESS_PACK_DIR", str(tmp_path / "packs"))
    monkeypatch.setenv("ASSESS_SYNC_INTERVAL", "12")
    config = AppConfig()
    assert config.api_base_url == "https://configured.invalid"
    assert config.database_path == tmp_path / "assessment-device.db"
    assert config.credential_path == tmp_path / "device_credentials.json"
    assert config.packs_directory == tmp_path / "packs"
    assert config.sync_interval_seconds == 12
    assert AppConfig(api_base_url=None).api_base_url is None
    with pytest.raises(ValueError):
        AppConfig(api_base_url="https://user:secret@example.invalid")
    with pytest.raises(ValueError):
        AppConfig(sync_interval_seconds=0)


def test_pairing_offline_does_not_create_credential(tmp_path):
    def offline(request):
        raise httpx.ConnectError("offline", request=request)

    with PairingClient("https://cloud.invalid", transport=httpx.MockTransport(offline)) as client:
        with pytest.raises(httpx.ConnectError):
            client.request("device-uuid")
    assert not (tmp_path / "device_credentials.json").exists()


def test_catalogue_uses_existing_versioned_download_reference():
    entry = dict(
        set_id="example",
        version=1,
        title="Example",
        subject="Science",
        chapter="Cells",
        question_count=20,
        size_bytes=1234,
        sha256="a" * 64,
        published_at=datetime(2026, 10, 27, tzinfo=UTC).isoformat(),
    )
    with ContentApiClient(
        "https://cloud.invalid",
        auth_token="local-credential",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"schema_version": 1, "packs": [entry]})
        ),
    ) as client:
        pack = client.fetch_catalog().packs[0]
    assert pack.download_reference == "/api/v1/content/packs/example/1"
    assert pack.sha256 == "a" * 64


def test_attempt_retry_keeps_uuid_and_idempotency_key():
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(503 if len(requests) == 1 else 201)

    payload = {"payload_version": 1, "attempt_id": "same-uuid"}
    with SyncApiClient(
        "https://cloud.invalid", auth_token="credential", transport=httpx.MockTransport(respond)
    ) as client:
        with pytest.raises(TransientSyncError):
            client.upload_attempt(payload, "same-uuid")
        assert client.upload_attempt(payload, "same-uuid").status_code == 201
    assert requests[0].content == requests[1].content
    assert all(request.headers["Idempotency-Key"] == "same-uuid" for request in requests)


def test_heartbeat_only_sends_operational_allowlist(monkeypatch):
    for name in ("DATABASE_URL", "PIN", "WIFI_PASSWORD", "PRIVATE_KEY"):
        monkeypatch.setenv(name, "secret-canary")
    requests = []

    def accept(request):
        requests.append(request)
        return httpx.Response(200, json={"status": "accepted"})

    with HeartbeatClient(
        "https://cloud.invalid",
        auth_token="credential-canary",
        transport=httpx.MockTransport(accept),
    ) as client:
        client.send(Heartbeat("0.1.0", 2, 3, 4096))
    body = json.loads(requests[0].content)
    assert set(body) == {
        "software_version",
        "installed_pack_count",
        "pending_attempt_count",
        "free_storage_bytes",
        "diagnostic_summary",
    }
    assert b"canary" not in requests[0].content
    assert requests[0].headers["Authorization"] == "Bearer credential-canary"
    with pytest.raises(ValueError):
        Heartbeat("0.1.0", 2, 3, 4096, "PIN=secret-canary").to_dict()


def test_offline_background_cycle_does_not_open_database(tmp_path):
    config = AppConfig(api_base_url=None, database_path=tmp_path / "unopened.db")
    run_cycle(config)
    assert not config.database_path.exists()
    with pytest.raises(ValueError, match="ASSESS_API_URL"):
        DeviceApi(config)


def test_release_report_without_backend(tmp_path, monkeypatch):
    from tools import release_check

    monkeypatch.setattr(release_check, "ROOT", tmp_path)
    assert release_check._backend_version() == "separate cloud repository"


def test_device_distribution_excludes_server_dependencies():
    import tomllib

    metadata = tomllib.loads(Path("pyproject.toml").read_text())
    dependencies = metadata["project"]["dependencies"]
    assert not any(
        name in " ".join(dependencies).lower()
        for name in ("fastapi", "sqlalchemy", "psycopg", "alembic", "supabase")
    )
    assert "backend" not in metadata["project"]["optional-dependencies"]


def test_background_cycle_uses_authenticated_clients_and_local_counts(tmp_path, monkeypatch):
    from app.auth.credentials import CredentialStore, DeviceCredential
    from app.sync import service

    config = AppConfig(api_base_url="https://cloud.invalid", database_path=tmp_path / "device.db",
                       credential_path=tmp_path / "credential.json")
    CredentialStore(config.credential_path).save(DeviceCredential("device-uuid", "credential"))
    received = []

    def accept(request):
        received.append(request)
        return httpx.Response(200, json={"status": "accepted"})

    monkeypatch.setattr(service, "DeviceApi", lambda config: DeviceApi(
        config, transport=httpx.MockTransport(accept)
    ))
    run_cycle(config)
    assert len(received) == 1
    assert received[0].url.path == "/api/v1/devices/heartbeat"
    assert received[0].headers["Authorization"] == "Bearer credential"
    body = json.loads(received[0].content)
    assert body["installed_pack_count"] == body["pending_attempt_count"] == 0
    assert body["free_storage_bytes"] > 0
