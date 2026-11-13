"""Signed release attack, staging, download, activation, and rollback tests."""

import base64
import json
import sqlite3
import tarfile
from io import BytesIO
from pathlib import Path

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.config import AppConfig
from app.data.db import run_migrations
from app.data.repo import Repository
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
from app.update.layout import (
    configured_installation_paths,
    migrate_existing_state,
    validate_trusted_app_root,
)
from app.update.manifest import UpdateManifest, canonical_manifest_bytes
from app.update.staging import stage_update
from app.update.verifier import verify_update
from tools import updater_service
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
        "release": {"version": version, "channel": "stable", "created_at": "2026-10-19T00:00:00Z", "min_supported_version": "0.1.0", "required_db_schema": 2, "notes": "Test release"},
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


def test_database_backup_preserves_profiles_attempts_outbox_and_credentials(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    database = data / "assessment.db"
    connection = sqlite3.connect(database)
    connection.executescript(
        "CREATE TABLE profiles(id TEXT PRIMARY KEY, name TEXT);"
        "CREATE TABLE attempts(id TEXT PRIMARY KEY, state TEXT);"
        "CREATE TABLE sync_outbox(id TEXT PRIMARY KEY, payload TEXT);"
        "INSERT INTO profiles VALUES('student-1','Learner');"
        "INSERT INTO attempts VALUES('attempt-1','completed');"
        "INSERT INTO sync_outbox VALUES('attempt-1','pending payload');"
    )
    connection.close()
    (data / "device_credentials.json").write_text('{"token":"preserved"}', encoding="utf-8")
    monkeypatch.setattr(updater_service, "DATA_ROOT", data)

    backup = updater_service._backup_database(database, tmp_path / "backups")

    assert backup is not None and backup.exists()
    connection = sqlite3.connect(backup)
    assert connection.execute("SELECT * FROM profiles").fetchall() == [("student-1", "Learner")]
    assert connection.execute("SELECT * FROM attempts").fetchall() == [("attempt-1", "completed")]
    assert connection.execute("SELECT * FROM sync_outbox").fetchall() == [
        ("attempt-1", "pending payload")
    ]
    connection.close()
    assert (backup.parent / "device_credentials.json").read_text(encoding="utf-8") == '{"token":"preserved"}'
    connection = sqlite3.connect(database)
    connection.execute("UPDATE profiles SET name='Learner after activation'")
    connection.execute("INSERT INTO attempts VALUES('attempt-2','completed')")
    connection.execute("INSERT INTO sync_outbox VALUES('attempt-2','pending after activation')")
    connection.commit()
    connection.close()
    (data / "device_credentials.json").write_text('{"token":"rotated after activation"}', encoding="utf-8")
    updater_service._restore_data_backup(database, backup, data / "device_credentials.json")
    connection = sqlite3.connect(database)
    assert connection.execute("SELECT name FROM profiles").fetchone() == ("Learner after activation",)
    assert connection.execute("SELECT * FROM attempts ORDER BY id").fetchall() == [
        ("attempt-1", "completed"), ("attempt-2", "completed")
    ]
    assert connection.execute("SELECT * FROM sync_outbox ORDER BY id").fetchall() == [
        ("attempt-1", "pending payload"), ("attempt-2", "pending after activation")
    ]
    connection.close()
    assert (data / "device_credentials.json").read_text(encoding="utf-8") == '{"token":"rotated after activation"}'


def test_first_time_state_migration_is_verified_and_never_overwrites(tmp_path):
    source = tmp_path / "legacy" / "var" / "assessment-device.db"
    source.parent.mkdir(parents=True)
    connection = sqlite3.connect(source)
    connection.executescript(
        "CREATE TABLE profiles(id TEXT PRIMARY KEY, name TEXT);"
        "CREATE TABLE attempts(id TEXT PRIMARY KEY, state TEXT);"
        "CREATE TABLE sync_outbox(id TEXT PRIMARY KEY, payload TEXT);"
        "INSERT INTO profiles VALUES('p1','Student');"
        "INSERT INTO attempts VALUES('a1','completed');"
        "INSERT INTO sync_outbox VALUES('a1','still pending');"
    )
    connection.close()
    source_credentials = source.parent / "device_credentials.json"
    source_credentials.write_text('{"device_id":"pi-1","token":"pairing"}', encoding="utf-8")
    target = tmp_path / "persistent-data" / "assessment-device.db"
    target_credentials = target.parent / "device_credentials.json"

    migrated_db, migrated_credentials = migrate_existing_state(
        source, target, source_credentials, target_credentials
    )

    assert migrated_db == target and migrated_credentials == target_credentials
    assert source.exists() and source_credentials.exists()
    connection = sqlite3.connect(target)
    assert connection.execute("SELECT * FROM profiles").fetchall() == [("p1", "Student")]
    assert connection.execute("SELECT * FROM attempts").fetchall() == [("a1", "completed")]
    assert connection.execute("SELECT * FROM sync_outbox").fetchall() == [("a1", "still pending")]
    connection.close()
    assert target_credentials.read_text(encoding="utf-8") == source_credentials.read_text(encoding="utf-8")

    target.write_bytes(b"existing database must not be replaced")
    target_credentials.unlink()
    with pytest.raises(FileExistsError, match="Refusing to overwrite existing database"):
        migrate_existing_state(source, target, source_credentials, target_credentials)
    assert target.read_bytes() == b"existing database must not be replaced"


def test_install_path_configuration_and_bad_database_locations(tmp_path):
    root = tmp_path / "aksh" / "assasement"
    data = tmp_path / "var-lib" / "questraa"
    configured = configured_installation_paths({
        "ASSESS_APP_ROOT": str(root),
        "ASSESS_DATA_DIR": str(data),
        "ASSESS_SQLITE_PATH": str(data / "device.sqlite"),
        "ASSESS_CREDENTIAL_PATH": str(data / "credentials.json"),
        "ASSESS_SERVICE_USER": "aksh",
        "ASSESS_SERVICE_GROUP": "aksh",
    })
    assert configured.app_root == root.resolve()
    assert configured.database_path == (data / "device.sqlite").resolve()
    assert configured.service_user == "aksh"
    assert configured.service_group == "aksh"

    with pytest.raises(ValueError, match="absolute"):
        configured_installation_paths({"ASSESS_SQLITE_PATH": "var/assessment.db"})
    with pytest.raises(ValueError, match="outside versioned release"):
        configured_installation_paths({
            "ASSESS_APP_ROOT": str(root),
            "ASSESS_DATA_DIR": str(data),
            "ASSESS_SQLITE_PATH": str(root / "releases" / "0.2.0" / "var" / "assessment.db"),
        })


def test_privileged_release_root_cannot_be_in_service_writable_home(tmp_path):
    current = tmp_path.stat()
    with pytest.raises(ValueError, match="service-writable ancestor"):
        validate_trusted_app_root(tmp_path / "managed-releases", current.st_uid, {current.st_gid})


def test_privileged_updater_copies_untrusted_artifact_before_verifying(tmp_path):
    source = tmp_path / "download.tar.gz"
    private_copy = tmp_path / "root-copy.tar.gz"
    source.write_bytes(b"signed bytes")
    assert updater_service._copy_untrusted_regular_file(source, private_copy, 1024) == 12
    source.write_bytes(b"changed by user after copy")
    assert private_copy.read_bytes() == b"signed bytes"


def test_persistent_sqlite_credentials_and_content_paths_are_configurable(monkeypatch, tmp_path):
    values = {
        "ASSESS_DATA_DIR": str(tmp_path / "persistent"),
        "ASSESS_SQLITE_PATH": str(tmp_path / "persistent" / "existing.db"),
        "ASSESS_CREDENTIAL_PATH": str(tmp_path / "persistent" / "pairing.json"),
        "ASSESS_PACK_DIR": str(tmp_path / "legacy" / "content"),
        "ASSESS_MEDIA_DIR": str(tmp_path / "legacy" / "media"),
        "ASSESS_DOWNLOAD_DIR": str(tmp_path / "legacy" / "recovery"),
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    config = AppConfig()
    assert config.database_path == Path(values["ASSESS_SQLITE_PATH"])
    assert config.credential_path == Path(values["ASSESS_CREDENTIAL_PATH"])
    assert config.packs_directory == Path(values["ASSESS_PACK_DIR"])
    assert config.media_directory == Path(values["ASSESS_MEDIA_DIR"])
    assert config.content_download_directory == Path(values["ASSESS_DOWNLOAD_DIR"])


def test_recovery_keeps_forward_migrated_database_for_previous_code(tmp_path):
    database = tmp_path / "device.db"
    with Repository(database) as initial:
        future_version = initial.schema_version + 1
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    connection.execute(
        "UPDATE schema_meta SET value=? WHERE key='schema_version'", (str(future_version),)
    )
    connection.commit()
    assert run_migrations(connection) == future_version
    assert connection.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()[0] == str(future_version)
    connection.close()
    with Repository(database) as repository:
        assert repository.schema_version == future_version
