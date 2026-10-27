from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.db.models import Device, DeviceCredential
from backend.app.main import create_app
from backend.app.services.pairing import hash_secret

TOKEN = "device_testid.test-secret-never-logged"
DEVICE_UUID = UUID("11111111-1111-4111-8111-111111111111")


def issue_test_credential(app, *, token: str = TOKEN, device_uuid: UUID = DEVICE_UUID) -> None:
    identifier, secret = token.removeprefix("device_").split(".", 1)
    with app.state.session_factory() as session:
        device = Device(
            device_id=device_uuid,
            display_name="Test device",
            status="active",
            created_at=datetime.now(UTC),
            paired_at=datetime.now(UTC),
        )
        session.add(device)
        session.flush()
        session.add(DeviceCredential(
            device_id=device.id,
            credential_id=identifier,
            secret_hash=hash_secret(secret),
            status="active",
            created_at=datetime.now(UTC),
        ))
        session.commit()


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    database_url = f"sqlite:///{(tmp_path / 'backend-test.db').as_posix()}"
    app = create_app(
        Settings(database_url=database_url, content_storage_path=tmp_path / "content")
    )
    with TestClient(app) as test_client:
        issue_test_credential(app)
        yield test_client
    app.state.engine.dispose()


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture
def payload() -> dict:
    attempt_id = "550e8400-e29b-41d4-a716-446655440000"
    return {
        "payload_version": 1,
        "attempt_id": attempt_id,
        "device_id": str(DEVICE_UUID),
        "profile": {"local_profile_id": "profile-1", "server_user_id": None},
        "question_set": {
            "set_id": "biology-1",
            "set_version": 3,
            "marking": {"correct": 4, "wrong": -1, "skip": 0},
        },
        "started_at": "2026-10-18T08:00:00Z",
        "completed_at": "2026-10-18T08:02:00Z",
        "duration_ms": 120000,
        "result": {"score": 3},
        "responses": [
            {
                "response_id": "response-1",
                "question_id": "question-1",
                "selected_key": "A",
                "confidence": "sure",
                "is_correct": True,
                "response_time_ms": 1200,
                "marked_review": False,
                "first_shown_at": "2026-10-18T08:00:01Z",
                "answered_at": "2026-10-18T08:00:03Z",
            },
            {
                "response_id": "response-2",
                "question_id": "question-2",
                "selected_key": None,
                "confidence": None,
                "is_correct": None,
                "response_time_ms": 900,
                "marked_review": True,
                "first_shown_at": "2026-10-18T08:00:04Z",
                "answered_at": None,
            },
        ],
    }


def upload_headers(auth_headers: dict[str, str], attempt_id: str) -> dict[str, str]:
    return {
        **auth_headers,
        "Idempotency-Key": attempt_id,
        "X-Attempt-Payload-Version": "1",
    }
