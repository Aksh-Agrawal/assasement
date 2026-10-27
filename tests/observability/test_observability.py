import io
import json
import logging
import sys
import zipfile
from argparse import Namespace
from datetime import UTC, datetime
from pathlib import Path

from app.assessment import AssessmentApplication
from app.auth.credentials import CredentialStore, DeviceCredential
from app.content.importer import import_pack
from app.core.models import Profile
from app.data.repo import Repository
from app.diagnostics import (
    HealthLevel,
    NetworkStatus,
    SecretRedactingFormatter,
    SecretRedactionFilter,
    collect_device_status,
)
from app.update.activation import ActivationManager
from tools import diagnose, pilot_check
from tools.create_support_bundle import create_support_bundle
from tools.diagnose import collect


def prepared_device(tmp_path: Path):
    database = tmp_path / "device.db"
    credentials = tmp_path / "credentials.json"
    with Repository(database) as repository:
        import_pack(Path("content/sample_biology.json"), repository)
    CredentialStore(credentials).save(
        DeviceCredential("11111111-1111-4111-8111-111111111111", "device_canary.secret")
    )
    return database, credentials


def snapshot(tmp_path: Path, network: NetworkStatus | None = None):
    database, credentials = prepared_device(tmp_path)
    with Repository(database) as repository:
        return collect_device_status(
            repository,
            database_path=database,
            credential_store=CredentialStore(credentials),
            update_manager=ActivationManager(tmp_path / "updates"),
            trusted_signing_key_id="test-key",
            network=network,
        )


def test_healthy_and_offline_snapshots(tmp_path: Path) -> None:
    healthy = snapshot(tmp_path / "healthy")
    assert healthy.health is HealthLevel.OK
    assert healthy.offline_assessment_ready
    offline = snapshot(
        tmp_path / "offline",
        NetworkStatus(checked=True, backend_reachable=False, error_code="BACKEND-001"),
    )
    assert offline.health is HealthLevel.DEGRADED
    assert offline.offline_assessment_ready
    assert "BACKEND-001" in offline.error_codes


def test_status_collection_does_not_mutate_repository(tmp_path: Path) -> None:
    database, credentials = prepared_device(tmp_path)
    with Repository(database) as repository:
        before = (
            repository.get_schema_meta(),
            repository.list_question_set_versions("biology-cell-practice-01"),
            repository.get_setting("last_content_sync_status"),
        )
        collect_device_status(
            repository,
            database_path=database,
            credential_store=CredentialStore(credentials),
            update_manager=ActivationManager(tmp_path / "updates"),
            trusted_signing_key_id="test-key",
        )
        after = (
            repository.get_schema_meta(),
            repository.list_question_set_versions("biology-cell-practice-01"),
            repository.get_setting("last_content_sync_status"),
        )
    assert after == before


def test_revoked_auth_snapshot_requires_action(tmp_path: Path) -> None:
    status = snapshot(
        tmp_path,
        NetworkStatus(
            checked=True,
            backend_reachable=True,
            database_ready=True,
            auth_accepted=False,
            catalog_reachable=False,
            error_code="AUTH-002",
        ),
    )
    assert status.health is HealthLevel.ACTION_REQUIRED
    assert status.device_revoked is True
    assert "AUTH-002" in status.error_codes


def test_corrupt_database_snapshot_is_stable_error(tmp_path: Path) -> None:
    database = tmp_path / "corrupt.db"
    database.write_bytes(b"not a sqlite database")
    status = collect(
        Namespace(
            db=database,
            credentials=tmp_path / "missing.json",
            base_url=None,
            update_root=tmp_path / "updates",
            trusted_key_id="test-key",
            connect_timeout=0.1,
            read_timeout=0.1,
            network=False,
        )
    )
    assert status["health"] == "ERROR"
    assert status["error_codes"] == ["DB-001"]
    assert database.read_bytes() == b"not a sqlite database"


def test_logging_filter_redacts_supported_secret_classes() -> None:
    canary = "private-canary-value"
    record = logging.LogRecord(
        "test",
        logging.INFO,
        __file__,
        1,
        "Authorization: Bearer device_public.secret DATABASE_URL=postgresql://user:password@host/db pairing code=123456 %s",
        (canary,),
        None,
    )
    assert SecretRedactionFilter(secrets=(canary,)).filter(record)
    rendered = record.getMessage()
    for secret in ("device_public.secret", "password", "123456", canary):
        assert secret not in rendered


def test_logging_formatter_redacts_exception_text() -> None:
    output = io.StringIO()
    handler = logging.StreamHandler(output)
    handler.setFormatter(SecretRedactingFormatter("%(message)s"))
    logger = logging.getLogger("observability-redaction-test")
    logger.handlers = [handler]
    logger.propagate = False
    try:
        raise RuntimeError("DATABASE_URL=postgresql://user:exception-secret@host/db")
    except RuntimeError:
        logger.exception("operation failed")
    assert "exception-secret" not in output.getvalue()


def test_support_bundle_excludes_secrets_database_and_answers(tmp_path: Path, monkeypatch) -> None:
    database, credentials = prepared_device(tmp_path)
    with Repository(database) as repository:
        profile = repository.create_profile(Profile("student-private", "Private Student"))
        app = AssessmentApplication(repository)
        attempt = app.start_test(profile.id, "biology-cell-practice-01", 1)
        app.select_answer("D")
        assert repository.get_response(attempt.id, app.current_question().id).selected_key == "D"
    logs = tmp_path / "logs"
    logs.mkdir()
    db_secret = "postgres-secret-canary"
    test_secret = "test-database-secret-canary"
    private_key = "-----BEGIN PRIVATE KEY-----\nprivate-key-canary\n-----END PRIVATE KEY-----"
    (logs / "assessment-device.log").write_text(
        f"Authorization: Bearer device_canary.secret\nDATABASE_URL={db_secret}\n"
        f"TEST_DATABASE_URL={test_secret}\npairing code=654321\n{private_key}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("DATABASE_URL", db_secret)
    monkeypatch.setenv("TEST_DATABASE_URL", test_secret)
    bundle = create_support_bundle(
        database_path=database,
        credential_path=credentials,
        log_directory=logs,
        update_root=tmp_path / "updates",
        output_directory=tmp_path / "support",
        trusted_key_id="test-key",
        now=datetime(2026, 10, 20, tzinfo=UTC),
    )
    with zipfile.ZipFile(bundle) as archive:
        names = archive.namelist()
        combined = "\n".join(
            archive.read(name).decode("utf-8", errors="replace") for name in names
        )
        diagnostics = json.loads(archive.read("diagnostics.json"))
    assert not any(name.endswith((".db", ".sqlite", ".sqlite3")) for name in names)
    for secret in (
        "device_canary.secret",
        db_secret,
        test_secret,
        "654321",
        "private-key-canary",
        "Private Student",
        "student-private",
    ):
        assert secret not in combined
        assert secret not in bundle.name
    assert "selected_key" not in json.dumps(diagnostics)
    assert diagnostics["attempts"][0]["attempt_ref"] != attempt.id


def test_diagnose_json_is_offline_by_default(tmp_path: Path, monkeypatch, capsys) -> None:
    database, credentials = prepared_device(tmp_path)
    monkeypatch.setattr(
        diagnose,
        "collect_network_status",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("network called")),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "diagnose",
            "--db",
            str(database),
            "--credentials",
            str(credentials),
            "--update-root",
            str(tmp_path / "updates"),
            "--json",
        ],
    )
    assert diagnose.main() == 0
    output = json.loads(capsys.readouterr().out)
    assert output["health"] == "OK"
    assert output["network"]["checked"] is False


def test_pilot_check_ready_offline_with_isolated_smoke(tmp_path: Path, monkeypatch, capsys) -> None:
    database, credentials = prepared_device(tmp_path)
    public_key = tmp_path / "public.pem"
    public_key.write_text("configured", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "pilot-check",
            "--db",
            str(database),
            "--credentials",
            str(credentials),
            "--update-root",
            str(tmp_path / "updates"),
            "--trusted-public-key",
            str(public_key),
        ],
    )
    assert pilot_check.main() == 0
    output = capsys.readouterr().out
    assert "PASS  Assessment smoke test" in output
    assert "PASS  Offline assessment readiness" in output
