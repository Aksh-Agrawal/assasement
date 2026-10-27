"""Local identity and credential behavior stays independent of assessment flow."""

import json
from pathlib import Path
from uuid import UUID

import httpx
import pytest

from app.auth.credentials import CredentialStore, DeviceCredential
from app.auth.device_identity import get_or_create_device_id
from app.data.repo import Repository
from app.sync.client import SyncApiClient
from app.sync.errors import PairingRequired


def test_device_uuid_is_created_once_and_survives_restart(tmp_path: Path) -> None:
    path = tmp_path / "device.db"
    with Repository(path) as repository:
        first = get_or_create_device_id(repository)
    with Repository(path) as repository:
        second = get_or_create_device_id(repository)
    assert UUID(first).version == 4
    assert second == first


def test_credential_store_round_trip_and_clear(tmp_path: Path) -> None:
    path = tmp_path / "credentials.json"
    store = CredentialStore(path)
    credential = DeviceCredential(device_id=str(UUID(int=4)), token="device_id.secret")
    assert store.load() is None
    store.save(credential)
    assert store.load() == credential
    assert json.loads(path.read_text(encoding="utf-8"))["token"] == credential.token
    store.clear()
    assert store.load() is None


def test_unpaired_client_stops_before_network_request() -> None:
    called = False

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(500)

    with SyncApiClient(
        "https://unused.invalid", transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(PairingRequired, match="PAIRING_REQUIRED"):
            client.upload_attempt({"payload_version": 1}, "attempt-id")
    assert called is False
