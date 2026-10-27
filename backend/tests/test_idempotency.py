from contextlib import nullcontext
from copy import deepcopy
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from backend.app.api.dependencies import AuthenticatedDevice
from backend.app.db.models import Attempt
from backend.app.schemas.attempts import AttemptUpload
from backend.app.services.attempts import ConflictingAttempt, payload_fingerprint, store_attempt
from backend.tests.conftest import upload_headers

DEVICE = AuthenticatedDevice(database_id=1, device_id="11111111-1111-4111-8111-111111111111")


def _put(client, auth_headers, payload):
    attempt_id = payload["attempt_id"]
    return client.put(
        f"/api/v1/attempts/{attempt_id}",
        json=payload,
        headers=upload_headers(auth_headers, attempt_id),
    )


def test_same_uuid_same_payload_is_idempotent(client, auth_headers, payload) -> None:
    assert _put(client, auth_headers, payload).status_code == 201
    repeated = _put(client, auth_headers, payload)
    assert repeated.status_code == 201
    assert repeated.json()["code"] == "already_uploaded"
    with client.app.state.session_factory() as session:
        assert session.scalar(select(func.count(Attempt.id))) == 1


def test_same_uuid_different_payload_conflicts_without_overwrite(
    client, auth_headers, payload
) -> None:
    assert _put(client, auth_headers, payload).status_code == 201
    changed = deepcopy(payload)
    changed["result"]["score"] = -1
    conflict = _put(client, auth_headers, changed)
    assert conflict.status_code == 409
    with client.app.state.session_factory() as session:
        stored = session.scalar(select(Attempt))
        assert stored is not None and stored.score == 3
        assert session.scalar(select(func.count(Attempt.id))) == 1


class RacingSession:
    """Minimal session double for a concurrent unique-constraint loser."""

    def __init__(self, stored_hash: str) -> None:
        self.stored_hash = stored_hash
        self.selects = 0
        self.rolled_back = False

    def scalar(self, _statement):
        self.selects += 1
        if self.selects == 1:
            return None
        return SimpleNamespace(payload_hash=self.stored_hash, authenticated_device_id=1)

    def begin_nested(self):
        return nullcontext()

    def add(self, _value) -> None:
        pass

    def flush(self) -> None:
        raise IntegrityError("insert", {}, RuntimeError("unique constraint"))

    def rollback(self) -> None:
        self.rolled_back = True


def test_unique_constraint_race_is_reconciled_by_payload_hash(payload) -> None:
    validated = AttemptUpload.model_validate(payload)
    session = RacingSession(payload_fingerprint(validated))
    result = store_attempt(session, validated, DEVICE)  # type: ignore[arg-type]
    assert result.already_uploaded is True
    assert session.rolled_back is True


def test_unique_constraint_race_with_different_hash_is_conflict(payload) -> None:
    validated = AttemptUpload.model_validate(payload)
    session = RacingSession("different")
    with pytest.raises(ConflictingAttempt):
        store_attempt(session, validated, DEVICE)  # type: ignore[arg-type]
    assert session.rolled_back is True
