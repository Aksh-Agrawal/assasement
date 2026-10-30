"""Signed release attack, staging, download, activation, and rollback tests."""

import base64
import json
import tarfile
from io import BytesIO
from pathlib import Path

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.update.activation import ActivationManager
from app.update.client import AvailableUpdate, UpdateClient
from app.update.errors import (
    CompatibilityError,
    IntegrityError,
    ManifestError,
    SignatureError,
    StagingError,
    UpdateError,
)
from app.update.manifest import UpdateManifest, canonical_manifest_bytes
from app.update.staging import stage_update
from app.update.verifier import verify_update
from tools.build_release import build_artifact

pytestmark = pytest.mark.update


def _bundle(tmp_path: Path, *, version="0.2.0", platform="development", malicious=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    artifact = tmp_path / f"assessment-device-{version}.tar.gz"
    if malicious:
        with tarfile.open(artifact, "w:gz") as archive:
            info = tarfile.TarInfo(malicious)
            data = b"evil"
            info.size = len(data)
            archive.addfile(info, BytesIO(data))
    else:
        build_artifact(Path.cwd(), artifact, version)
    import hashlib

    manifest = {
        "schema_version": 1,
        "signing_key_id": "test-key",
        "release": {"version": version, "channel": "stable", "created_at": "2026-10-19T00:00:00Z", "min_supported_version": "0.1.0", "required_db_schema": 2},
        "artifact": {"filename": artifact.name, "size_bytes": artifact.stat().st_size, "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()},
        "compatibility": {"platform": platform, "architecture": "any"},
    }
    private = Ed25519PrivateKey.generate()
    raw = canonical_manifest_bytes(manifest)
    return raw, private.sign(raw), artifact, private


def _verify(raw, signature, artifact, private, **changes):
    options = {"current_version": "0.1.0", "platform": "development", "architecture": "any", "db_schema": 2}
    options.update(changes)
    return verify_update(raw, signature, artifact, trusted_keys={"test-key": private.public_key()}, **options)


def test_valid_signed_release_and_semantic_version(tmp_path: Path) -> None:
    raw, signature, artifact, private = _bundle(tmp_path, version="0.10.0")
    verified = _verify(raw, signature, artifact, private, current_version="0.9.0")
    assert str(verified.manifest.version) == "0.10.0"
    second = tmp_path / "second.tar.gz"
    build_artifact(Path.cwd(), second, "0.10.0")
    assert artifact.read_bytes() == second.read_bytes()


def test_tampered_manifest_artifact_wrong_key_and_bad_schema(tmp_path: Path) -> None:
    raw, signature, artifact, private = _bundle(tmp_path)
    changed = json.loads(raw)
    changed["release"]["created_at"] = "2026-10-20T00:00:00Z"
    with pytest.raises(SignatureError):
        _verify(canonical_manifest_bytes(changed), signature, artifact, private)
    data = bytearray(artifact.read_bytes())
    data[-1] ^= 1
    artifact.write_bytes(data)
    with pytest.raises(IntegrityError):
        _verify(raw, signature, artifact, private)
    raw2, signature2, artifact2, _ = _bundle(tmp_path / "wrong")
    with pytest.raises(SignatureError):
        _verify(raw2, signature2, artifact2, Ed25519PrivateKey.generate())
    malformed = json.loads(raw2)
    del malformed["artifact"]["sha256"]
    with pytest.raises(ManifestError):
        _verify(canonical_manifest_bytes(malformed), signature2, artifact2, private)


@pytest.mark.parametrize(
    ("version", "platform", "current"),
    [("0.1.0", "development", "0.1.0"), ("0.0.9", "development", "0.1.0"), ("0.2.0", "wrong", "0.1.0")],
)
def test_same_downgrade_and_wrong_platform_rejected(tmp_path, version, platform, current) -> None:
    raw, signature, artifact, private = _bundle(tmp_path, version=version, platform=platform)
    with pytest.raises(CompatibilityError):
        _verify(raw, signature, artifact, private, current_version=current)


def test_size_truncation_and_malicious_paths_rejected_before_activation(tmp_path: Path) -> None:
    raw, signature, artifact, private = _bundle(tmp_path / "truncated")
    artifact.write_bytes(artifact.read_bytes()[:-20])
    with pytest.raises(IntegrityError, match="size"):
        _verify(raw, signature, artifact, private)
    for index, name in enumerate(("../../evil", "/etc/file", "C:\\evil")):
        raw, signature, artifact, private = _bundle(tmp_path / str(index), malicious=name)
        verified = _verify(raw, signature, artifact, private)
        with pytest.raises(StagingError, match="unsafe"):
            stage_update(verified, tmp_path / f"stage-{index}")


def test_atomic_staging_success_activation_and_rollback(tmp_path: Path) -> None:
    raw, signature, artifact, private = _bundle(tmp_path / "good")
    verified = _verify(raw, signature, artifact, private)
    root = tmp_path / "runtime"
    staged = stage_update(verified, root)
    manager = ActivationManager(root)
    current = tmp_path / "current"
    current.mkdir()
    (current / "marker").write_text("old", encoding="utf-8")
    manager.initialize("0.1.0", current)
    assert manager.activate(staged, "0.2.0", lambda _path: True)
    assert manager.metadata() == {"current": "0.2.0", "previous": "0.1.0", "staged": None, "status": "healthy"}

    raw, signature, artifact, private = _bundle(tmp_path / "bad-health", version="0.3.0")
    staged = stage_update(_verify(raw, signature, artifact, private, current_version="0.2.0"), root)
    assert manager.activate(staged, "0.3.0", lambda _path: False) is False
    assert manager.metadata()["current"] == "0.2.0"
    assert manager.metadata()["previous"] == "0.3.0"
    assert manager.metadata()["status"] == "rolled_back"


class InterruptedStream(httpx.SyncByteStream):
    def __iter__(self):
        yield b"partial"
        raise httpx.ReadError("connection lost")


def test_interrupted_download_removes_partial_file(tmp_path: Path) -> None:
    raw, _signature, _artifact, _private = _bundle(tmp_path / "source")
    manifest = UpdateManifest.parse(raw)
    update = AvailableUpdate(raw, b"signature", manifest)
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, stream=InterruptedStream()))
    destination = tmp_path / "download.tar.gz"
    client = UpdateClient("https://updates.invalid", "device_x.y", transport=transport)
    with pytest.raises(httpx.ReadError):
        client.download_update(update, destination)
    client.close()
    assert not destination.exists()
    assert not destination.with_suffix(destination.suffix + ".part").exists()


def test_authenticated_update_check_and_download_limit(tmp_path: Path) -> None:
    raw, signature, _artifact, _private = _bundle(tmp_path / "source")
    manifest_data = json.loads(raw)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer device_x.y"
        return httpx.Response(
            200,
            json={
                "manifest": manifest_data,
                "signature": base64.b64encode(signature).decode("ascii"),
            },
        )

    client = UpdateClient(
        "https://updates.invalid",
        "device_x.y",
        transport=httpx.MockTransport(handler),
    )
    update = client.check_for_update()
    with pytest.raises(IntegrityError, match="size limit"):
        client.download_update(update, tmp_path / "blocked.tar.gz", hard_max_bytes=1)
    client.close()


def test_update_check_auth_failure_is_non_installing(tmp_path: Path) -> None:
    client = UpdateClient(
        "https://updates.invalid",
        "revoked",
        transport=httpx.MockTransport(lambda _request: httpx.Response(401)),
    )
    with pytest.raises(UpdateError, match="authentication"):
        client.check_for_update()
    client.close()
    assert not list(tmp_path.iterdir())


def test_no_published_update_is_benign_without_warning(caplog):
    client = UpdateClient("https://updates.invalid", "device_x.y",
        transport=httpx.MockTransport(lambda _request: httpx.Response(404)))
    assert client.check_for_update() is None
    client.close()
    assert not [record for record in caplog.records if record.levelno >= 30]
