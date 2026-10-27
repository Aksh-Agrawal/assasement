"""Real localhost Phase 9A device-to-Phase 9B backend integration."""

import socket
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import uvicorn
from sqlalchemy import func, select

from app.assessment import AssessmentApplication
from app.content.importer import import_pack
from app.core.models import Confidence, Profile
from app.data.repo import Repository, SyncStatus
from app.sync.client import SyncApiClient
from app.sync.payloads import build_upload_payload
from app.sync.policy import SyncPolicy
from app.sync.worker import SyncWorker
from backend.app.config import Settings
from backend.app.db.models import Attempt, AttemptResponse
from backend.app.main import create_app
from backend.tests.conftest import TOKEN, issue_test_credential

PROFILE_ID = "550e8400-e29b-41d4-a716-446655440001"


class LocalUvicorn:
    def __init__(self, app) -> None:
        self.socket = socket.socket()
        self.socket.bind(("127.0.0.1", 0))
        self.port = self.socket.getsockname()[1]
        self.server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=self.port, log_level="warning")
        )
        self.thread = threading.Thread(
            target=self.server.run, kwargs={"sockets": [self.socket]}, daemon=True
        )

    def start(self) -> None:
        self.thread.start()
        for _ in range(100):
            if self.server.started:
                return
            time.sleep(0.02)
        raise RuntimeError("Uvicorn did not start")

    def stop(self) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=5)
        self.socket.close()

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"


def complete_offline_assessment(repository: Repository) -> str:
    if repository.get_question_set("biology-cell-practice-01", 1) is None:
        import_pack(Path("content/sample_biology.json"), repository)
    if repository.get_profile(PROFILE_ID) is None:
        repository.create_profile(
            Profile(id=PROFILE_ID, display_name="Local integration student"),
            created_at=datetime.now(UTC),
        )

    application = AssessmentApplication(repository)
    attempt = application.start_test(PROFILE_ID, "biology-cell-practice-01", 1, shuffle_seed=9)
    application.select_answer(application.current_question().correct_key)
    application.set_confidence(Confidence.SURE)
    application.next_question()
    application.pause()

    application = AssessmentApplication(repository)
    assert application.resume_attempt(PROFILE_ID) is not None
    application.previous_question()
    application.next_question()
    for index in range(1, 20):
        application.select_answer(application.current_question().correct_key)
        application.continue_unrated()
        if index < 19:
            application.next_question()
    application.request_submit()
    application.submit()
    assert len(application.open_review()) == 20
    return attempt.id


def test_real_client_lost_ack_idempotency_and_offline_recovery(tmp_path: Path) -> None:
    backend_url = f"sqlite:///{(tmp_path / 'backend-e2e.db').as_posix()}"
    backend_app = create_app(Settings(database_url=backend_url))
    server = LocalUvicorn(backend_app)
    device_path = tmp_path / "device-e2e.db"

    with Repository(device_path, device_id="device-e2e") as repository:
        first_id = complete_offline_assessment(repository)
        assert repository.get_attempt_sync_state(first_id).status is SyncStatus.PENDING
        payload = build_upload_payload(repository, first_id)

        server.start()
        issue_test_credential(backend_app)
        with SyncApiClient(server.base_url, auth_token=TOKEN) as client:
            # The backend commits, but the device never records this acknowledgement.
            first_http = client.upload_attempt(payload, first_id)
            assert first_http.status_code == 201
        assert repository.get_attempt_sync_state(first_id).status is SyncStatus.PENDING

        with SyncApiClient(server.base_url, auth_token=TOKEN) as client:
            recovered = SyncWorker(repository, client).run_sync_once()
            retry_http = client.upload_attempt(payload, first_id)
        assert recovered.synced == 1
        assert retry_http.status_code == 201
        assert repository.get_attempt_sync_state(first_id).status is SyncStatus.SYNCED

        with backend_app.state.session_factory() as session:
            assert session.scalar(select(func.count(Attempt.id))) == 1
            assert session.scalar(select(func.count(AttemptResponse.id))) == 20
            stored = session.scalar(select(Attempt))
            assert stored is not None and stored.question_set_version == 1

        # A second full assessment remains fully usable while FastAPI is unavailable.
        server.stop()
        second_id = complete_offline_assessment(repository)
        assert repository.get_attempt_sync_state(second_id).status is SyncStatus.PENDING
        with SyncApiClient(server.base_url, auth_token=TOKEN, connect_timeout=0.2) as client:
            failed = SyncWorker(
                repository,
                client,
                policy=SyncPolicy(initial_retry_seconds=1),
                clock=lambda: datetime.now(UTC),
            ).run_sync_once()
        assert failed.transient_failures == 1
        assert repository.get_attempt_sync_state(second_id).status is SyncStatus.FAILED

        restarted = LocalUvicorn(backend_app)
        restarted.start()
        repository.requeue_failed_attempt(second_id)
        with SyncApiClient(restarted.base_url, auth_token=TOKEN) as client:
            restored = SyncWorker(
                repository,
                client,
                clock=lambda: datetime.now(UTC) + timedelta(seconds=2),
            ).run_sync_once()
        assert restored.synced == 1
        assert repository.get_attempt_sync_state(second_id).status is SyncStatus.SYNCED
        restarted.stop()

    backend_app.state.engine.dispose()
