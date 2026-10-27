"""Pairing, authentication, revocation, and server-authoritative ownership."""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select

from backend.app.db.models import Attempt, Device, DeviceCredential, PairingSession
from backend.app.services.pairing import approve_pairing, revoke_device
from backend.tests.conftest import upload_headers


def _request(client, device_id=None):
    return client.post(
        "/api/v1/pairing/request",
        json={"device_id": str(device_id or uuid4()), "device_name": "Laptop test"},
    )


def _approve(client, code: str, *, now: datetime | None = None) -> None:
    with client.app.state.session_factory() as session:
        approve_pairing(session, code, now=now or datetime.now(UTC))


def _claim(client, body: dict) -> str:
    response = client.post(
        f"/api/v1/pairing/{body['session_id']}/claim",
        headers={"X-Pairing-Claim": body["claim_secret"]},
    )
    assert response.status_code == 200
    assert set(response.json()) == {"credential"}
    return response.json()["credential"]


def test_request_approve_status_claim_is_single_use_and_hash_only(client) -> None:
    response = _request(client)
    assert response.status_code == 201
    body = response.json()
    assert len(body["pairing_code"]) == 6 and body["pairing_code"].isdigit()
    assert set(body) == {"session_id", "pairing_code", "claim_secret", "expires_at"}
    headers = {"X-Pairing-Claim": body["claim_secret"]}
    status = client.get(f"/api/v1/pairing/{body['session_id']}/status", headers=headers)
    assert status.json() == {"status": "pending"}
    _approve(client, body["pairing_code"])
    assert client.get(
        f"/api/v1/pairing/{body['session_id']}/status", headers=headers
    ).json() == {"status": "approved"}
    token = _claim(client, body)
    assert client.post(
        f"/api/v1/pairing/{body['session_id']}/claim", headers=headers
    ).status_code == 409
    with client.app.state.session_factory() as session:
        credential = session.scalars(
            select(DeviceCredential).order_by(DeviceCredential.id.desc())
        ).first()
        pairing = session.get(PairingSession, UUID(body["session_id"]))
        assert credential is not None and token not in credential.secret_hash
        assert token.split(".", 1)[1] not in credential.secret_hash
        assert pairing is not None and pairing.status == "consumed"
        assert body["claim_secret"] not in pairing.claim_secret_hash


def test_wrong_code_and_expired_code_are_safely_rejected(client) -> None:
    response = _request(client)
    body = response.json()
    late = datetime.fromisoformat(body["expires_at"].replace("Z", "+00:00")) + timedelta(seconds=1)
    with client.app.state.session_factory() as session:
        for code in ("999999", body["pairing_code"]):
            try:
                approve_pairing(session, code, now=late)
            except RuntimeError as error:
                assert str(error) == "Invalid, expired, or already-used pairing code"
            else:
                raise AssertionError("approval unexpectedly succeeded")


def test_authenticated_owner_revocation_and_fresh_repair(client, payload, caplog) -> None:
    device_id = uuid4()
    first = _request(client, device_id).json()
    _approve(client, first["pairing_code"])
    old_token = _claim(client, first)
    payload["device_id"] = str(uuid4())  # spoofed body identity must be ignored
    attempt_id = payload["attempt_id"]
    with caplog.at_level(logging.INFO):
        accepted = client.put(
            f"/api/v1/attempts/{attempt_id}",
            json=payload,
            headers=upload_headers({"Authorization": f"Bearer {old_token}"}, attempt_id),
        )
    assert accepted.status_code == 201
    assert old_token not in caplog.text
    with client.app.state.session_factory() as session:
        stored = session.scalar(
            select(Attempt).where(Attempt.device_attempt_id == UUID(payload["attempt_id"]))
        )
        assert stored is not None and stored.device_id == str(device_id)
        device = session.scalar(select(Device).where(Device.device_id == device_id))
        assert device is not None
        revoke_device(session, device_id, now=datetime.now(UTC))
    other_id = str(uuid4())
    payload["attempt_id"] = other_id
    assert client.put(
        f"/api/v1/attempts/{other_id}",
        json=payload,
        headers=upload_headers({"Authorization": f"Bearer {old_token}"}, other_id),
    ).status_code == 401
    second = _request(client, device_id).json()
    _approve(client, second["pairing_code"])
    new_token = _claim(client, second)
    assert new_token != old_token
    assert client.put(
        f"/api/v1/attempts/{other_id}",
        json=payload,
        headers=upload_headers({"Authorization": f"Bearer {new_token}"}, other_id),
    ).status_code == 201
    assert client.put(
        f"/api/v1/attempts/{other_id}",
        json=payload,
        headers=upload_headers({"Authorization": f"Bearer {old_token}"}, other_id),
    ).status_code == 401
