from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

from backend.app.api.routes import attempts as attempt_routes
from backend.app.db.models import Attempt, AttemptResponse
from backend.tests.conftest import upload_headers


def test_valid_attempt_and_responses_are_stored(client, auth_headers, payload) -> None:
    attempt_id = payload["attempt_id"]
    response = client.put(
        f"/api/v1/attempts/{attempt_id}",
        json=payload,
        headers=upload_headers(auth_headers, attempt_id),
    )
    assert response.status_code == 201
    assert response.json() == {
        "status": "accepted",
        "attempt_id": attempt_id,
        "code": "accepted",
    }
    with client.app.state.session_factory() as session:
        stored = session.scalar(select(Attempt))
        assert stored is not None
        assert stored.question_set_id == "biology-1"
        assert stored.question_set_version == 3
        assert session.scalar(select(func.count(AttemptResponse.id))) == 2


def test_authentication_required_and_invalid_token_rejected(client, payload) -> None:
    attempt_id = payload["attempt_id"]
    headers = {"Idempotency-Key": attempt_id, "X-Attempt-Payload-Version": "1"}
    assert client.put(f"/api/v1/attempts/{attempt_id}", json=payload, headers=headers).status_code == 401
    headers["Authorization"] = "Bearer wrong"
    assert client.put(f"/api/v1/attempts/{attempt_id}", json=payload, headers=headers).status_code == 401


def test_schema_validation_and_business_validation(client, auth_headers, payload) -> None:
    attempt_id = payload["attempt_id"]
    invalid = {**payload, "duration_ms": -1}
    response = client.put(
        f"/api/v1/attempts/{attempt_id}",
        json=invalid,
        headers=upload_headers(auth_headers, attempt_id),
    )
    assert response.status_code == 422

    response = client.put(
        f"/api/v1/attempts/{attempt_id}",
        json=payload,
        headers=upload_headers(auth_headers, "00000000-0000-4000-8000-000000000001"),
    )
    assert response.status_code == 400


def test_transaction_rolls_back_when_a_response_constraint_fails(
    client, auth_headers, payload
) -> None:
    attempt_id = payload["attempt_id"]
    payload["responses"][1]["question_id"] = payload["responses"][0]["question_id"]
    response = client.put(
        f"/api/v1/attempts/{attempt_id}",
        json=payload,
        headers=upload_headers(auth_headers, attempt_id),
    )
    assert response.status_code == 400
    with client.app.state.session_factory() as session:
        assert session.scalar(select(func.count(Attempt.id))) == 0
        assert session.scalar(select(func.count(AttemptResponse.id))) == 0


def test_database_unavailable_returns_retryable_503(
    client, auth_headers, payload, monkeypatch
) -> None:
    def unavailable(_session, _payload, _device):
        raise OperationalError("select", {}, RuntimeError("database unavailable"))

    monkeypatch.setattr(attempt_routes, "store_attempt", unavailable)
    attempt_id = payload["attempt_id"]
    response = client.put(
        f"/api/v1/attempts/{attempt_id}",
        json=payload,
        headers=upload_headers(auth_headers, attempt_id),
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "Backend database unavailable"}
