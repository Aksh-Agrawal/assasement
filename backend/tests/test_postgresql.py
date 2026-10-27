"""Opt-in PostgreSQL migration and real device sync integration tests."""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import delete, func, inspect, select
from sqlalchemy.engine import make_url

from app.assessment import AssessmentApplication
from app.auth.credentials import CredentialStore
from app.auth.device_identity import get_or_create_device_id
from app.auth.pairing import PairingClient
from app.content.client import ContentApiClient
from app.content.sync import ContentSyncStatus, sync_content_once
from app.core.models import Profile
from app.data.repo import Repository, SyncStatus
from app.sync.client import SyncApiClient
from app.sync.payloads import build_upload_payload
from app.sync.worker import SyncWorker
from backend.app.config import Settings
from backend.app.db.models import (
    Attempt,
    AttemptResponse,
    Device,
    DeviceCredential,
    PairingSession,
    QuestionPack,
)
from backend.app.db.session import create_database_engine, create_session_factory
from backend.app.main import create_app
from backend.app.schemas.attempts import AttemptUpload
from backend.app.services.attempts import payload_fingerprint
from backend.app.services.content import publish_pack_bytes
from backend.app.services.pairing import approve_pairing
from backend.tests.conftest import issue_test_credential
from backend.tests.test_end_to_end import LocalUvicorn, complete_offline_assessment

pytestmark = pytest.mark.postgres
TOKEN = "device_postgres.postgres-integration-secret"


@pytest.fixture(scope="module")
def postgres_url() -> str:
    value = os.environ.get("TEST_DATABASE_URL")
    if not value:
        pytest.skip("TEST_DATABASE_URL is not configured")
    parsed = make_url(value)
    if not parsed.drivername.startswith("postgresql"):
        pytest.fail("TEST_DATABASE_URL must use PostgreSQL")
    if not parsed.database or "test" not in parsed.database.lower():
        pytest.fail("Refusing destructive integration tests outside a database named with 'test'")
    return value


@pytest.fixture(scope="module")
def migrated_postgres(postgres_url: str) -> str:
    config = Config("backend/alembic.ini")
    config.attributes["database_url"] = postgres_url
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    command.upgrade(config, "head")
    return postgres_url


@pytest.fixture(autouse=True)
def clean_application_rows(migrated_postgres: str):
    engine = create_database_engine(migrated_postgres)
    factory = create_session_factory(engine)
    with factory() as session, session.begin():
        session.execute(delete(QuestionPack))
        session.execute(delete(AttemptResponse))
        session.execute(delete(Attempt))
        session.execute(delete(DeviceCredential))
        session.execute(delete(PairingSession))
        session.execute(delete(Device))
    engine.dispose()
    yield


def _headers(attempt_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {TOKEN}",
        "Idempotency-Key": attempt_id,
        "X-Attempt-Payload-Version": "1",
    }


def test_postgres_migration_schema_and_constraints(migrated_postgres: str) -> None:
    engine = create_database_engine(migrated_postgres)
    inspector = inspect(engine)
    assert {
        "alembic_version", "attempts", "attempt_responses", "devices",
        "pairing_sessions", "device_credentials", "question_packs",
    } <= set(
        inspector.get_table_names()
    )
    attempt_uniques = {item["name"] for item in inspector.get_unique_constraints("attempts")}
    response_uniques = {
        item["name"] for item in inspector.get_unique_constraints("attempt_responses")
    }
    foreign_keys = inspector.get_foreign_keys("attempt_responses")
    assert "uq_attempts_device_attempt_id" in attempt_uniques
    assert "uq_attempt_responses_attempt_question" in response_uniques
    assert foreign_keys[0]["referred_table"] == "attempts"
    assert foreign_keys[0]["options"].get("ondelete") == "RESTRICT"
    pack_uniques = {
        tuple(item["column_names"])
        for item in inspector.get_unique_constraints("question_packs")
    }
    assert ("set_id", "version") in pack_uniques
    engine.dispose()


def test_postgres_response_failure_rolls_back_entire_attempt(
    migrated_postgres: str, payload: dict
) -> None:
    application = create_app(Settings(database_url=migrated_postgres))
    server = LocalUvicorn(application)
    server.start()
    issue_test_credential(application, token=TOKEN)
    attempt_id = payload["attempt_id"]
    payload["responses"][1]["question_id"] = payload["responses"][0]["question_id"]
    response = httpx.put(
        f"{server.base_url}/api/v1/attempts/{attempt_id}",
        json=payload,
        headers=_headers(attempt_id),
    )
    server.stop()
    assert response.status_code == 400

    engine = create_database_engine(migrated_postgres)
    with create_session_factory(engine)() as session:
        assert session.scalar(select(func.count(Attempt.id))) == 0
        assert session.scalar(select(func.count(AttemptResponse.id))) == 0
    engine.dispose()


def test_real_device_sync_idempotency_restart_and_failure_recovery(
    migrated_postgres: str, tmp_path: Path
) -> None:
    application = create_app(Settings(database_url=migrated_postgres))
    server = LocalUvicorn(application)
    server.start()
    readiness = httpx.get(f"{server.base_url}/ready")
    assert readiness.status_code == 200
    assert readiness.json()["database"] == "ok"
    assert readiness.json()["migration"] == "current"
    device_path = tmp_path / "postgres-device.db"
    credential_path = tmp_path / "postgres-device-credential.json"

    with Repository(device_path) as repository:
        device_id = get_or_create_device_id(repository)
        credential_store = CredentialStore(credential_path)
        with PairingClient(server.base_url) as pairing_client:
            pairing = pairing_client.request(device_id, "PostgreSQL integration device")
            with application.state.session_factory() as session:
                approve_pairing(session, pairing.code, now=datetime.now(UTC))
            pairing_client.claim(pairing, credential_store, device_id)
        stored_credential = credential_store.load()
        assert stored_credential is not None
        paired_token = stored_credential.token
        attempt_id = complete_offline_assessment(repository)
        assert repository.get_attempt_sync_state(attempt_id).status is SyncStatus.PENDING
        payload = build_upload_payload(repository, attempt_id)

        # PostgreSQL commits, while local state deliberately remains pending (lost ACK).
        with SyncApiClient(server.base_url, auth_token=paired_token) as client:
            assert client.upload_attempt(payload, attempt_id).status_code == 201
        assert repository.get_attempt_sync_state(attempt_id).status is SyncStatus.PENDING

        with SyncApiClient(server.base_url, auth_token=paired_token) as client:
            recovered = SyncWorker(repository, client).run_sync_once()
            assert client.upload_attempt(payload, attempt_id).status_code == 201
        assert recovered.synced == 1
        assert repository.get_attempt_sync_state(attempt_id).status is SyncStatus.SYNCED

        with application.state.session_factory() as session:
            stored = session.scalar(select(Attempt).where(Attempt.device_attempt_id == uuid4()))
            assert stored is None
            stored = session.scalar(select(Attempt))
            assert stored is not None
            assert str(stored.device_attempt_id) == attempt_id
            assert stored.question_set_version == payload["question_set"]["set_version"]
            assert stored.score == payload["result"]["score"]
            assert stored.payload_hash == payload_fingerprint(AttemptUpload.model_validate(payload))
            responses = session.scalars(
                select(AttemptResponse)
                .where(AttemptResponse.attempt_id == stored.id)
                .order_by(AttemptResponse.id)
            ).all()
            assert len(responses) == len(payload["responses"])
            assert responses[0].confidence == payload["responses"][0]["confidence"]
            assert responses[0].response_time_ms == payload["responses"][0]["response_time_ms"]

        changed = deepcopy(payload)
        changed["result"]["score"] += 1
        conflict = httpx.put(
            f"{server.base_url}/api/v1/attempts/{attempt_id}",
            json=changed,
            headers={**_headers(attempt_id), "Authorization": f"Bearer {paired_token}"},
        )
        assert conflict.status_code == 409

        raced = deepcopy(payload)
        raced_id = str(uuid4())
        raced["attempt_id"] = raced_id

        def upload_raced() -> int:
            return httpx.put(
                f"{server.base_url}/api/v1/attempts/{raced_id}",
                json=raced,
                headers={**_headers(raced_id), "Authorization": f"Bearer {paired_token}"},
            ).status_code

        with ThreadPoolExecutor(max_workers=2) as executor:
            assert list(executor.map(lambda _value: upload_raced(), range(2))) == [201, 201]
        with application.state.session_factory() as session:
            assert session.scalar(
                select(func.count(Attempt.id)).where(Attempt.device_attempt_id == uuid4())
            ) == 0
            assert session.scalar(select(func.count(Attempt.id))) == 2

        conflicting_id = str(uuid4())
        first_conflict = deepcopy(payload)
        first_conflict["attempt_id"] = conflicting_id
        second_conflict = deepcopy(first_conflict)
        second_conflict["result"]["score"] += 1

        def upload_conflicting(body: dict) -> int:
            return httpx.put(
                f"{server.base_url}/api/v1/attempts/{conflicting_id}",
                json=body,
                headers={
                    **_headers(conflicting_id),
                    "Authorization": f"Bearer {paired_token}",
                },
            ).status_code

        with ThreadPoolExecutor(max_workers=2) as executor:
            statuses = list(executor.map(upload_conflicting, (first_conflict, second_conflict)))
        assert sorted(statuses) == [201, 409]

        # Backend restart uses a new engine and retains PostgreSQL data.
        server.stop()
        next_id = complete_offline_assessment(repository)
        restarted_app = create_app(Settings(database_url=migrated_postgres))
        restarted = LocalUvicorn(restarted_app)
        restarted.start()
        with SyncApiClient(restarted.base_url, auth_token=paired_token) as client:
            assert SyncWorker(repository, client).run_sync_once().synced == 1
        assert repository.get_attempt_sync_state(next_id).status is SyncStatus.SYNCED

        # An unreachable PostgreSQL endpoint yields HTTP 500 and a retryable local failure.
        failed_id = complete_offline_assessment(repository)
        restarted.stop()
        dead_url = str(make_url(migrated_postgres).set(host="127.0.0.1", port=1))
        unavailable_app = create_app(Settings(database_url=dead_url))
        unavailable = LocalUvicorn(unavailable_app)
        unavailable.start()
        with SyncApiClient(unavailable.base_url, auth_token=paired_token) as client:
            failed = SyncWorker(repository, client).run_sync_once()
        unavailable.stop()
        assert failed.transient_failures == 1
        assert repository.get_attempt_sync_state(failed_id).status is SyncStatus.FAILED

        repository.requeue_failed_attempt(failed_id)
        restored_app = create_app(Settings(database_url=migrated_postgres))
        restored = LocalUvicorn(restored_app)
        restored.start()
        with SyncApiClient(restored.base_url, auth_token=paired_token) as client:
            assert SyncWorker(repository, client).run_sync_once().synced == 1
        assert repository.get_attempt_sync_state(failed_id).status is SyncStatus.SYNCED
        restored.stop()

    final_engine = create_database_engine(migrated_postgres)
    with create_session_factory(final_engine)() as session:
        assert session.scalar(select(func.count(Attempt.id))) == 5
        stored_hash = session.scalar(select(DeviceCredential.secret_hash))
        assert stored_hash is not None
        assert paired_token not in stored_hash
        assert paired_token.split(".", 1)[1] not in stored_hash
    final_engine.dispose()


def test_real_postgres_content_flow_preserves_active_attempt(
    migrated_postgres: str, tmp_path: Path
) -> None:
    storage = tmp_path / "server-content"
    application = create_app(
        Settings(database_url=migrated_postgres, content_storage_path=storage)
    )
    server = LocalUvicorn(application)
    server.start()
    database = tmp_path / "content-device.db"
    credential_store = CredentialStore(tmp_path / "content-credential.json")
    v1 = Path("content/sample_biology.json").read_bytes()
    v2_value = json.loads(v1)
    v2_value["set"]["version"] = 2
    v2_value["questions"][0]["question_text"] = "PostgreSQL published version 2"
    v2 = json.dumps(v2_value, ensure_ascii=False, separators=(",", ":")).encode()

    with Repository(database) as repository:
        device_id = get_or_create_device_id(repository)
        with PairingClient(server.base_url) as pairing_client:
            pairing = pairing_client.request(device_id, "Content integration device")
            with application.state.session_factory() as session:
                approve_pairing(session, pairing.code, now=datetime.now(UTC))
            pairing_client.claim(pairing, credential_store, device_id)
        credential = credential_store.load()
        assert credential is not None

        with application.state.session_factory() as session:
            publish_pack_bytes(v1, session=session, storage_root=storage)
        with ContentApiClient(server.base_url, auth_token=credential.token) as client:
            first = sync_content_once(
                repository,
                client,
                temp_directory=tmp_path / "downloads",
                max_pack_bytes=25 * 1024 * 1024,
                max_downloads_per_cycle=5,
            )
        assert first.packs[0].status is ContentSyncStatus.INSTALLED

        student = repository.create_profile(Profile("postgres-student", "Student"))
        assessment = AssessmentApplication(repository)
        attempt = assessment.start_test(student.id, "biology-cell-practice-01", 1, shuffle_seed=9)
        order = repository.get_attempt_question_order(attempt.id)
        assessment.select_answer("A")

        with application.state.session_factory() as session:
            publish_pack_bytes(v2, session=session, storage_root=storage)
        with ContentApiClient(server.base_url, auth_token=credential.token) as client:
            second = sync_content_once(
                repository,
                client,
                temp_directory=tmp_path / "downloads",
                max_pack_bytes=25 * 1024 * 1024,
                max_downloads_per_cycle=5,
            )
        assert any(item.status is ContentSyncStatus.INSTALLED for item in second.packs)
        assert repository.get_active_question_set("biology-cell-practice-01").version == 2

    with Repository(database) as repository:
        resumed = AssessmentApplication(repository).resume_attempt(student.id)
        assert resumed is not None and resumed.set_version == 1
        assert repository.get_attempt_question_order(attempt.id) == order
        next_student = repository.create_profile(Profile("postgres-student-2", "Student 2"))
        new_attempt = AssessmentApplication(repository).start_test(
            next_student.id, "biology-cell-practice-01", 2
        )
        assert new_attempt.set_version == 2
    server.stop()
