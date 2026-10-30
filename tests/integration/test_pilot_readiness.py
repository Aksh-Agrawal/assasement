"""WAL-safe pilot backup and full-prefix preservation without ownership inference."""
import json
import shutil
import sqlite3
import zipfile
from pathlib import Path
from uuid import uuid4

import pytest

from app.assessment import AssessmentApplication
from app.content.importer import import_pack
from app.core.models import Profile
from app.data.db import MIGRATIONS_DIRECTORY, connect_database, run_migrations
from app.data.repo import Repository
from app.diagnostics import redact_text
from app.sync.payloads import build_upload_payload
from tools.backup_device import backup
from tools.create_support_bundle import create_support_bundle
from tools.pilot_inventory import inventory
from tools.restore_local_db import restore


def seeded(path):
    with Repository(path) as repo:
        repo.create_profile(Profile("legacy", "Legacy"))
        import_pack(Path("content/sample_biology.json"), repo)
        engine = AssessmentApplication(repo)
        attempt = engine.start_test("legacy", "biology-cell-practice-01", 1)
        engine.select_answer("A")
        engine.continue_unrated()
        engine.request_submit()
        engine.submit()
        return attempt.id


@pytest.mark.parametrize("prefix", [2, 3, 4, 5, 6])
def test_every_device_prefix_preserves_evidence_and_pending_sync(tmp_path, prefix):
    # Populate a pre-redesign-style DB using actual current domain data, then retain
    # only columns/tables present in each real historical migration prefix.
    original = tmp_path / "original.db"
    attempt = seeded(original)
    limited = tmp_path / "migrations"
    limited.mkdir()
    for file in sorted(MIGRATIONS_DIRECTORY.glob("*.sql"))[:prefix]:
        shutil.copyfile(file, limited / file.name)
    target = tmp_path / "legacy.db"
    connection = connect_database(target)
    assert run_migrations(connection, limited) == prefix
    with sqlite3.connect(original) as source:
        for table in ("profiles", "question_sets", "questions", "attempts", "attempt_questions", "responses"):
            cols = [r[1] for r in connection.execute('PRAGMA table_info("' + table + '")')]
            names = ','.join('"' + c + '"' for c in cols)
            rows = source.execute('SELECT ' + names + ' FROM "' + table + '"').fetchall()
            connection.executemany('INSERT INTO "' + table + '" (' + names + ') VALUES (' + ','.join('?' for _ in cols) + ')', rows)
    before = {t: [tuple(r) for r in connection.execute('SELECT * FROM "' + t + '"')] for t in ("profiles", "attempts", "responses", "question_sets", "attempt_questions")}
    run_migrations(connection)
    run_migrations(connection)
    for table, rows in before.items():
        after = [tuple(r) for r in connection.execute('SELECT * FROM "' + table + '"')]
        assert [r[:len(rows[0])] for r in after] == rows
    connection.close()
    with Repository(target) as repo:
        assert repo.get_profile("legacy").ownership_state == "legacy_unclaimed"
        assert repo.get_attempt_sync_state(attempt).status.value == "pending"
        assert "ownership" not in build_upload_payload(repo, attempt)
        repo.apply_profile_link("legacy", {"status":"linked", "local_profile_id":"legacy", "link_id":str(uuid4()), "student_account_id":str(uuid4()),
            "study_profile_id":str(uuid4()), "account_display_name":"Student", "study_profile_name":"NEET"})
        assert repo.get_profile("legacy").link_state == "linked"
        assert "ownership" not in build_upload_payload(repo, attempt)


def test_live_wal_backup_restore_inventory_and_no_missing_db_creation(tmp_path):
    path = tmp_path / "live.db"
    attempt = seeded(path)
    credentials = tmp_path / "credentials.json"
    credentials.write_text('{"device_id":"fixture","token":"private-token"}')
    with Repository(path) as repo:
        repo.set_setting("committed_in_wal", "retained")
        snapshot = inventory(path, credentials)
        manifest = backup(path, tmp_path / "backup", credentials=credentials)
        assert manifest["inventory"]["counts"] == snapshot["counts"]
        assert manifest["inventory"]["integrity_ok"]
        assert "private-token" not in json.dumps(manifest)
        with pytest.raises(FileExistsError):
            backup(path, tmp_path / "backup")
    restored = tmp_path / "restored.db"
    restore(tmp_path / "backup/assessment-device.db", restored)
    with Repository(restored) as repo:
        assert repo.get_setting("committed_in_wal") == "retained"
        assert repo.get_attempt_sync_state(attempt).status.value == "pending"
    with pytest.raises(sqlite3.OperationalError):
        inventory(tmp_path / "missing.db")
    assert not (tmp_path / "missing.db").exists()


def test_support_bundle_redacts_pilot_secrets(tmp_path):
    database = tmp_path / "db"
    seeded(database)
    logs = tmp_path / "logs"
    logs.mkdir()
    secrets = ["password=secret-password", '"token": "secret-token"', "wifi_password=secret-wifi",
               "SUPABASE_SERVICE_ROLE_KEY=secret-service", "ENR-secret-enrollment"]
    (logs / "assessment-device.log").write_text(' '.join(secrets))
    output = create_support_bundle(database_path=database, credential_path=tmp_path / "none",
        log_directory=logs, update_root=tmp_path / "updates", output_directory=tmp_path / "support",
        trusted_key_id="public")
    with zipfile.ZipFile(output) as bundle:
        content = '\n'.join(bundle.read(n).decode() for n in bundle.namelist())
        for secret in ("secret-password", "secret-token", "secret-wifi", "secret-service", "secret-enrollment"):
            assert secret not in content
        assert not any(n.endswith('.db') for n in bundle.namelist())
    assert "private" not in redact_text("password_hash=private")


def test_operator_retry_preserves_exact_upload_evidence(tmp_path, monkeypatch):
    from datetime import UTC, datetime

    from app.ui.controller import UIController
    from tools.retry_upload import main

    database = tmp_path / "device.db"
    attempt = seeded(database)
    with Repository(database) as repo:
        before = build_upload_payload(repo, attempt)
        repo.mark_attempt_syncing(attempt, started_at=datetime.now(UTC))
        repo.mark_attempt_sync_failed(attempt, error="HTTP 404: upload rejected",
                                      error_kind="permanent", next_sync_at=None)
        assert UIController(repo).sync_label == "Failed"
    monkeypatch.setenv("ASSESS_SQLITE_PATH", str(database))
    monkeypatch.setattr("sys.argv", ["retry_upload", attempt])
    assert main() == 0
    with Repository(database) as repo:
        assert build_upload_payload(repo, attempt) == before
        assert repo.get_attempt_sync_state(attempt).status.value == "pending"
