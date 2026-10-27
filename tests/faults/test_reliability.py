"""Deterministic file-backed crash, rollback, backup, and recovery campaign."""

import sqlite3
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from sqlalchemy import func, select

from app.assessment import AssessmentApplication
from app.auth.credentials import CredentialStore
from app.content.importer import import_pack
from app.core.models import AttemptStatus, Confidence, Profile
from app.data.db import check_integrity, connect_database, transaction
from app.data.repo import LocalDatabaseIntegrityError, Repository, SyncStatus
from app.sync.client import SyncApiClient
from app.sync.payloads import build_upload_payload
from app.sync.worker import SyncWorker
from backend.app.config import Settings
from backend.app.db.models import Attempt
from backend.app.main import create_app
from backend.tests.conftest import TOKEN, issue_test_credential
from backend.tests.test_end_to_end import LocalUvicorn
from tests.faults.harness import FaultInjector, InjectedCrash
from tools.restore_local_db import restore

pytestmark = pytest.mark.fault
NOW = datetime(2026, 10, 19, 8, 0, tzinfo=UTC)
PROFILE = "990e8400-e29b-41d4-a716-446655440000"


def _started(path: Path, faults: FaultInjector | None = None):
    repository = Repository(path, fault_hook=faults or (lambda _point: None))
    import_pack(Path("content/sample_biology.json"), repository, now=NOW)
    repository.create_profile(Profile(id=PROFILE, display_name="Fault Student"), created_at=NOW)
    app = AssessmentApplication(repository, wall_clock=lambda: NOW)
    attempt = app.start_test(PROFILE, "biology-cell-practice-01", 1, shuffle_seed=7)
    return repository, app, attempt


def test_response_before_and_after_commit_partial_confidence_and_review(tmp_path: Path) -> None:
    path = tmp_path / "response.db"
    faults = FaultInjector()
    repository, app, attempt = _started(path, faults)
    question_id = app.current_question().id
    faults.arm("BEFORE_RESPONSE_COMMIT")
    with pytest.raises(InjectedCrash):
        app.select_answer("B")
    repository.close()
    with Repository(path) as reopened:
        response = reopened.get_response(attempt.id, question_id)
        assert response is not None and response.selected_key is None
        assert reopened.integrity_check().ok

    faults = FaultInjector()
    repository = Repository(path, fault_hook=faults)
    app = AssessmentApplication(repository, wall_clock=lambda: NOW)
    assert app.resume_attempt(PROFILE) is not None
    faults.arm("AFTER_RESPONSE_COMMIT")
    with pytest.raises(InjectedCrash):
        app.select_answer("B")
    repository.close()
    with Repository(path) as reopened:
        response = reopened.get_response(attempt.id, question_id)
        assert response is not None
        assert response.selected_key == "B" and response.confidence is Confidence.UNRATED
        assert response.response_time_ms >= 0 and response.marked_review is False
        resumed = AssessmentApplication(reopened, wall_clock=lambda: NOW)
        resumed.resume_attempt(PROFILE)
        order = reopened.get_attempt_question_order(attempt.id)
        resumed.go_to_question(order.index(question_id))
        resumed.set_marked_review(True)
    with Repository(path) as reopened:
        response = reopened.get_response(attempt.id, question_id)
        assert response is not None and response.marked_review
        assert response.confidence is Confidence.UNRATED


def test_navigation_order_and_completion_commit_boundaries(tmp_path: Path) -> None:
    path = tmp_path / "completion.db"
    faults = FaultInjector()
    repository, app, attempt = _started(path, faults)
    order = repository.get_attempt_question_order(attempt.id)
    app.select_answer(app.current_question().correct_key)
    app.continue_unrated()
    app.next_question()
    repository.close()
    repository = Repository(path, fault_hook=faults)
    app = AssessmentApplication(repository, wall_clock=lambda: NOW)
    app.resume_attempt(PROFILE)
    assert repository.get_attempt_question_order(attempt.id) == order
    app.request_submit()
    faults.arm("BEFORE_ATTEMPT_COMPLETION_COMMIT")
    with pytest.raises(InjectedCrash):
        app.submit()
    assert repository.get_attempt(attempt.id).status is AttemptStatus.IN_PROGRESS
    repository.close()
    repository = Repository(path, fault_hook=faults)
    app = AssessmentApplication(repository, wall_clock=lambda: NOW)
    app.resume_attempt(PROFILE)
    app.request_submit()
    faults.arm("AFTER_ATTEMPT_COMPLETION_COMMIT")
    with pytest.raises(InjectedCrash):
        app.submit()
    repository.close()
    with Repository(path) as reopened:
        completed = reopened.get_attempt(attempt.id)
        state = reopened.get_attempt_sync_state(attempt.id)
        assert completed.status is AttemptStatus.COMPLETED
        assert completed.completed_at is not None and completed.score is not None
        assert completed.duration_ms >= 0 and state.status is SyncStatus.PENDING
        assert reopened.find_in_progress_attempt(PROFILE) is None
        assert reopened.integrity_check().ok
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute(
            "SELECT COUNT(*) FROM attempts WHERE "
            "(status='completed' AND score IS NULL) OR "
            "(status='in_progress' AND completed_at IS NOT NULL)"
        ).fetchone()[0] == 0


def test_wal_rollback_backup_restore_and_corruption_detection(tmp_path: Path) -> None:
    path = tmp_path / "wal.db"
    with Repository(path) as repository:
        repository.set_setting("committed", "yes")
        backup = tmp_path / "snapshot.db"
        repository.backup_to(backup)
    connection = connect_database(path)
    with pytest.raises(InjectedCrash):
        with transaction(connection) as active:
            active.execute("INSERT INTO settings(key,value) VALUES ('uncommitted','no')")
            raise InjectedCrash("power loss")
    connection.close()
    with Repository(path) as reopened:
        assert reopened.get_setting("committed") == "yes"
        assert reopened.get_setting("uncommitted") is None
        reopened.set_setting("after_backup", "new")
    with sqlite3.connect(backup) as snapshot:
        assert check_integrity(snapshot).ok
        assert snapshot.execute("SELECT value FROM settings WHERE key='after_backup'").fetchone() is None
    restored = tmp_path / "restored.db"
    assert restore(backup, restored) is None
    with Repository(restored) as repository:
        assert repository.get_setting("committed") == "yes"
    corrupt = tmp_path / "corrupt.db"
    corrupt.write_bytes(backup.read_bytes()[:128])
    with pytest.raises(LocalDatabaseIntegrityError, match="LOCAL_DATABASE_ERROR"):
        Repository(corrupt)


def test_pack_import_fault_rolls_back_and_attempt_remains_version_pinned(tmp_path: Path) -> None:
    path = tmp_path / "pack.db"
    faults = FaultInjector()
    repository, _app, attempt = _started(path, faults)
    version_one = repository.get_question_set(attempt.set_id, 1)
    faults.arm("BEFORE_PACK_IMPORT_COMMIT")
    with pytest.raises(InjectedCrash):
        repository.import_question_set(replace(version_one, version=2), content_hash="v2")
    repository.close()
    with Repository(path) as reopened:
        assert reopened.get_question_set(attempt.set_id, 2) is None
        assert reopened.get_active_question_set(attempt.set_id).version == 1
        assert reopened.get_attempt(attempt.id).set_version == 1
        assert reopened.integrity_check().ok


def test_sync_crash_stale_recovery_http_failure_and_lost_ack(tmp_path: Path) -> None:
    path = tmp_path / "sync.db"
    repository, app, attempt = _started(path)
    app.request_submit()
    app.submit()
    faults = FaultInjector()
    faults.arm("AFTER_SYNC_MARKED_SYNCING")
    with SyncApiClient("https://mock.invalid", auth_token="device_x.y", transport=httpx.MockTransport(lambda _r: httpx.Response(201))) as client:
        with pytest.raises(InjectedCrash):
            SyncWorker(repository, client, clock=lambda: NOW, fault_hook=faults).run_sync_once()
    assert repository.get_attempt_sync_state(attempt.id).status is SyncStatus.SYNCING
    with Repository(path) as competing_repository:
        with SyncApiClient("https://mock.invalid", auth_token="device_x.y", transport=httpx.MockTransport(lambda _r: httpx.Response(201))) as client:
            assert SyncWorker(competing_repository, client, clock=lambda: NOW).run_sync_once().selected == 0
    interrupted = httpx.MockTransport(lambda request: (_ for _ in ()).throw(httpx.ReadError("lost", request=request)))
    with SyncApiClient("https://mock.invalid", auth_token="device_x.y", transport=interrupted) as client:
        result = SyncWorker(repository, client, clock=lambda: NOW + timedelta(minutes=10)).run_sync_once()
    assert result.transient_failures == 1
    assert repository.get_attempt(attempt.id) is not None
    repository.requeue_failed_attempt(attempt.id)
    faults.arm("BEFORE_LOCAL_SYNC_ACK")
    with SyncApiClient("https://mock.invalid", auth_token="device_x.y", transport=httpx.MockTransport(lambda _r: httpx.Response(201))) as client:
        with pytest.raises(InjectedCrash):
            SyncWorker(repository, client, clock=lambda: NOW + timedelta(minutes=20), fault_hook=faults).run_sync_once()
    assert repository.get_attempt_sync_state(attempt.id).status is SyncStatus.SYNCING
    with SyncApiClient("https://mock.invalid", auth_token="device_x.y", transport=httpx.MockTransport(lambda request: httpx.Response(409, json={"code":"already_uploaded","attempt_id":request.headers["Idempotency-Key"]}))) as client:
        result = SyncWorker(repository, client, clock=lambda: NOW + timedelta(minutes=30)).run_sync_once()
    assert result.already_synced == 1
    assert repository.get_attempt_sync_state(attempt.id).status is SyncStatus.SYNCED


def test_missing_and_malformed_credentials_do_not_touch_database(tmp_path: Path) -> None:
    database = tmp_path / "offline.db"
    repository, app, attempt = _started(database)
    app.request_submit()
    app.submit()
    malformed = tmp_path / "credentials.json"
    malformed.write_text("not json", encoding="utf-8")
    assert CredentialStore(tmp_path / "missing.json").load() is None
    with pytest.raises(ValueError):
        CredentialStore(malformed).load()
    assert CredentialStore(malformed).load_safe() is None
    assert repository.get_attempt(attempt.id) is not None
    assert repository.get_attempt_sync_state(attempt.id).status is SyncStatus.PENDING


def test_full_crash_offline_lost_ack_recovery_has_one_server_attempt(tmp_path: Path) -> None:
    device_path = tmp_path / "full-device.db"
    repository, app, attempt = _started(device_path)
    app.select_answer(app.current_question().correct_key)
    app.continue_unrated()
    app.next_question()
    app.select_answer(app.current_question().correct_key)
    repository.close()  # simulated application termination
    repository = Repository(device_path)
    resumed = AssessmentApplication(repository, wall_clock=lambda: NOW)
    assert resumed.resume_attempt(PROFILE).id == attempt.id
    resumed.request_submit()
    resumed.submit()
    assert repository.get_attempt_sync_state(attempt.id).status is SyncStatus.PENDING

    with SyncApiClient(
        "https://offline.invalid",
        auth_token=TOKEN,
        transport=httpx.MockTransport(lambda _request: httpx.Response(503)),
    ) as client:
        assert SyncWorker(repository, client, clock=lambda: NOW).run_sync_once().transient_failures == 1
    repository.requeue_failed_attempt(attempt.id)

    backend_url = f"sqlite:///{(tmp_path / 'full-backend.db').as_posix()}"
    backend_app = create_app(Settings(database_url=backend_url))
    server = LocalUvicorn(backend_app)
    server.start()
    issue_test_credential(backend_app)
    payload = build_upload_payload(repository, attempt.id)
    with SyncApiClient(server.base_url, auth_token=TOKEN) as client:
        assert client.upload_attempt(payload, attempt.id).status_code == 201
        assert repository.get_attempt_sync_state(attempt.id).status is SyncStatus.PENDING
        assert SyncWorker(repository, client, clock=lambda: NOW + timedelta(minutes=1)).run_sync_once().synced == 1
    with backend_app.state.session_factory() as session:
        assert session.scalar(select(func.count(Attempt.id))) == 1
    server.stop()
    repository.close()
