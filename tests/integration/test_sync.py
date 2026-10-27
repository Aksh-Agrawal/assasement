"""Laptop-only mocked HTTP coverage for the Phase 9A sync architecture."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import httpx
import pytest

from app.core.models import (
    Attempt,
    Confidence,
    MarkingScheme,
    Option,
    Profile,
    Question,
    QuestionSet,
    Response,
)
from app.data.repo import Repository, SyncStatus
from app.sync.client import SyncApiClient
from app.sync.payloads import build_upload_payload
from app.sync.policy import SyncPolicy
from app.sync.worker import SyncWorker

NOW = datetime(2026, 10, 17, 6, 30, tzinfo=UTC)
SET_ID = "biology-sync-01"
PROFILE_ID = "550e8400-e29b-41d4-a716-446655440000"


def _question(question_id: str, position: int, correct_key: str) -> Question:
    return Question(
        id=question_id,
        position=position,
        topic="Sync",
        difficulty=1,
        question_text=f"Question {position}",
        options=tuple(
            Option(key=key, text=f"Option {key}") for key in ("A", "B", "C", "D")
        ),
        correct_key=correct_key,  # type: ignore[arg-type]
    )


def _seed(repository: Repository) -> None:
    repository.create_profile(Profile(id=PROFILE_ID, display_name="Student"), created_at=NOW)
    repository.import_question_set(
        QuestionSet(
            id=SET_ID,
            version=3,
            title="Sync Set",
            subject="Biology",
            chapter="Offline",
            marking=MarkingScheme(),
            questions=(
                _question("q2", 2, "B"),
                _question("q1", 1, "A"),
            ),
        ),
        content_hash="sha256:sync",
        downloaded_at=NOW,
        is_active=True,
    )


def _completed_attempt(
    repository: Repository,
    number: int = 1,
    *,
    completed_at: datetime | None = None,
) -> str:
    attempt_id = str(UUID(int=number))
    started_at = NOW + timedelta(seconds=number)
    repository.create_attempt(
        Attempt(
            id=attempt_id,
            profile_id=PROFILE_ID,
            set_id=SET_ID,
            set_version=3,
            started_at=started_at,
        ),
        question_order=("q2", "q1"),
    )
    repository.save_response(
        Response(
            id=f"response-{number}-q2",
            attempt_id=attempt_id,
            question_id="q2",
            selected_key="A",
            confidence=Confidence.SURE,
            response_time_ms=1200,
            marked_review=True,
        ),
        is_correct=False,
        first_shown_at=started_at,
        answered_at=started_at + timedelta(seconds=2),
    )
    repository.save_response(
        Response(
            id=f"response-{number}-q1",
            attempt_id=attempt_id,
            question_id="q1",
            selected_key="A",
            confidence=Confidence.NOT_SURE,
            response_time_ms=800,
        ),
        is_correct=True,
        first_shown_at=started_at + timedelta(seconds=3),
        answered_at=started_at + timedelta(seconds=4),
    )
    repository.complete_attempt(
        attempt_id,
        completed_at=completed_at or NOW + timedelta(minutes=number),
        duration_ms=2000,
        score=3,
    )
    return attempt_id


def _client(handler) -> SyncApiClient:
    return SyncApiClient(
        "https://mock.invalid",
        transport=httpx.MockTransport(handler),
        auth_token="device_mock.mock-secret",
    )


def test_success_marks_synced_and_sends_stable_identity(tmp_path: Path) -> None:
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(201, json={"status": "accepted"})

    with Repository(tmp_path / "success.db", device_id="device-local") as repository:
        _seed(repository)
        attempt_id = _completed_attempt(repository)
        before = repository.get_attempt_responses(attempt_id)
        with _client(handler) as client:
            result = SyncWorker(repository, client, clock=lambda: NOW + timedelta(hours=1)).run_sync_once()

        state = repository.get_attempt_sync_state(attempt_id)
        assert result.synced == 1
        assert state.status is SyncStatus.SYNCED
        assert state.synced_at == NOW + timedelta(hours=1)
        assert state.attempts == 0
        assert state.last_error is None
        assert repository.get_attempt_responses(attempt_id) == before
        assert seen[0].headers["Idempotency-Key"] == attempt_id
        assert seen[0].url.path.endswith(attempt_id)
        assert seen[0].extensions["timeout"] == {
            "connect": 5.0,
            "read": 15.0,
            "write": 15.0,
            "pool": 5.0,
        }


@pytest.mark.parametrize(
    ("name", "failure"),
    [
        ("offline", httpx.ConnectError("connection refused")),
        ("timeout", httpx.ReadTimeout("read timed out")),
    ],
)
def test_transport_failure_is_retryable_and_local_data_remains(
    tmp_path: Path, name: str, failure: Exception
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise failure

    with Repository(tmp_path / f"{name}.db") as repository:
        _seed(repository)
        attempt_id = _completed_attempt(repository)
        attempt_before = repository.get_attempt(attempt_id)
        responses_before = repository.get_attempt_responses(attempt_id)
        with _client(handler) as client:
            result = SyncWorker(repository, client, clock=lambda: NOW + timedelta(hours=1)).run_sync_once()

        state = repository.get_attempt_sync_state(attempt_id)
        assert result.transient_failures == 1
        assert state.status is SyncStatus.FAILED
        assert state.error_kind == "transient"
        assert state.attempts == 1
        assert state.next_sync_at == NOW + timedelta(hours=1, seconds=5)
        assert repository.get_attempt(attempt_id) == attempt_before
        assert repository.get_attempt_responses(attempt_id) == responses_before


@pytest.mark.parametrize(
    ("status_code", "kind", "count_field"),
    [
        (500, "transient", "transient_failures"),
        (400, "permanent", "permanent_failures"),
        (401, "authentication", "authentication_failures"),
    ],
)
def test_http_failures_are_classified(
    tmp_path: Path, status_code: int, kind: str, count_field: str
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"code": "test"})

    with Repository(tmp_path / f"http-{status_code}.db") as repository:
        _seed(repository)
        attempt_id = _completed_attempt(repository)
        with _client(handler) as client:
            result = SyncWorker(repository, client, clock=lambda: NOW + timedelta(hours=1)).run_sync_once()

        state = repository.get_attempt_sync_state(attempt_id)
        assert getattr(result, count_field) == 1
        assert state.status is SyncStatus.FAILED
        assert state.error_kind == kind
        assert state.attempts == 1
        assert repository.get_attempt(attempt_id) is not None
        if kind == "transient":
            assert state.next_sync_at is not None
        else:
            assert state.next_sync_at is None
            assert repository.get_sync_eligible_attempts(
                now=NOW + timedelta(days=1), limit=10, max_attempts=5
            ) == ()


def test_already_uploaded_after_uncertain_crash_is_success(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        attempt_id = request.headers["Idempotency-Key"]
        return httpx.Response(
            409,
            json={"code": "already_uploaded", "attempt_id": attempt_id},
        )

    with Repository(tmp_path / "already.db") as repository:
        _seed(repository)
        attempt_id = _completed_attempt(repository)
        repository.mark_attempt_syncing(attempt_id, started_at=NOW)
        with _client(handler) as client:
            result = SyncWorker(
                repository,
                client,
                policy=SyncPolicy(stale_syncing_seconds=60),
                clock=lambda: NOW + timedelta(minutes=2),
            ).run_sync_once()

        state = repository.get_attempt_sync_state(attempt_id)
        assert result.recovered_stale == 1
        assert result.already_synced == 1
        assert state.status is SyncStatus.SYNCED


def test_payload_is_deterministic_and_uses_exact_set_version(tmp_path: Path) -> None:
    with Repository(tmp_path / "payload.db", device_id="device-local") as repository:
        _seed(repository)
        attempt_id = _completed_attempt(repository)
        first = build_upload_payload(repository, attempt_id)
        second = build_upload_payload(repository, attempt_id)

    assert first == second
    assert first["attempt_id"] == attempt_id
    assert first["question_set"]["set_id"] == SET_ID
    assert first["question_set"]["set_version"] == 3
    assert [item["question_id"] for item in first["responses"]] == ["q2", "q1"]
    assert first["responses"][0]["is_correct"] is False
    assert first["result"] == {"score": 3.0}


def test_batch_limit_and_oldest_first_order(tmp_path: Path) -> None:
    uploaded = []

    def handler(request: httpx.Request) -> httpx.Response:
        uploaded.append(request.headers["Idempotency-Key"])
        return httpx.Response(204)

    with Repository(tmp_path / "batch.db") as repository:
        _seed(repository)
        ids = [_completed_attempt(repository, number) for number in range(1, 6)]
        with _client(handler) as client:
            result = SyncWorker(
                repository,
                client,
                policy=SyncPolicy(batch_size=2),
                clock=lambda: NOW + timedelta(hours=1),
            ).run_sync_once()

        assert result.selected == 2
        assert uploaded == ids[:2]
        assert [repository.get_attempt_sync_state(item).status for item in ids] == [
            SyncStatus.SYNCED,
            SyncStatus.SYNCED,
            SyncStatus.PENDING,
            SyncStatus.PENDING,
            SyncStatus.PENDING,
        ]


def test_dry_local_completion_never_constructs_network_client(tmp_path: Path) -> None:
    with Repository(tmp_path / "offline-completion.db") as repository:
        _seed(repository)
        attempt_id = _completed_attempt(repository)
        assert repository.get_attempt(attempt_id) is not None
        assert repository.get_attempt_sync_state(attempt_id).status is SyncStatus.PENDING


def test_max_retry_limit_preserves_failed_attempt_without_reselecting(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    policy = SyncPolicy(max_automatic_retries=2, initial_retry_seconds=1)
    with Repository(tmp_path / "retry-limit.db") as repository:
        _seed(repository)
        attempt_id = _completed_attempt(repository)
        with _client(handler) as client:
            SyncWorker(repository, client, policy=policy, clock=lambda: NOW).run_sync_once()
            SyncWorker(
                repository,
                client,
                policy=policy,
                clock=lambda: NOW + timedelta(seconds=1),
            ).run_sync_once()
            third = SyncWorker(
                repository,
                client,
                policy=policy,
                clock=lambda: NOW + timedelta(days=1),
            ).run_sync_once()

        state = repository.get_attempt_sync_state(attempt_id)
        assert third.selected == 0
        assert state.status is SyncStatus.FAILED
        assert state.attempts == 2
        assert state.next_sync_at is None
        assert repository.get_attempt(attempt_id) is not None

        repository.requeue_failed_attempt(attempt_id)
        requeued = repository.get_attempt_sync_state(attempt_id)
        assert requeued.status is SyncStatus.PENDING
        assert requeued.attempts == 0
