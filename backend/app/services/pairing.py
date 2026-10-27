"""Transactional pairing, credential issuance, and revocation operations."""

import hashlib
import hmac
import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.app.db.models import Device, DeviceCredential, PairingSession

LOGGER = logging.getLogger(__name__)


class PairingRejected(RuntimeError):
    pass


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


@dataclass(frozen=True, slots=True)
class NewPairing:
    session_id: UUID
    code: str
    claim_secret: str
    expires_at: datetime


def request_pairing(
    session: Session,
    device_uuid: UUID,
    display_name: str | None,
    *,
    now: datetime,
    ttl_seconds: int,
) -> NewPairing:
    device = session.scalar(select(Device).where(Device.device_id == device_uuid))
    if device is None:
        device = Device(
            device_id=device_uuid,
            display_name=display_name,
            status="pending",
            created_at=now,
        )
        session.add(device)
        session.flush()
    elif display_name is not None:
        device.display_name = display_name
    for _ in range(20):
        code = f"{secrets.randbelow(1_000_000):06d}"
        if session.scalar(select(PairingSession.id).where(PairingSession.code_hash == hash_secret(code))) is None:
            break
    else:
        raise RuntimeError("Could not allocate a pairing code")
    claim_secret = secrets.token_urlsafe(32)
    pairing = PairingSession(
        id=uuid4(),
        device_id=device.id,
        code_hash=hash_secret(code),
        claim_secret_hash=hash_secret(claim_secret),
        status="pending",
        created_at=now,
        expires_at=now + timedelta(seconds=ttl_seconds),
    )
    session.add(pairing)
    session.commit()
    return NewPairing(pairing.id, code, claim_secret, pairing.expires_at)


def approve_pairing(session: Session, code: str, *, now: datetime) -> UUID:
    pairing = session.scalar(
        select(PairingSession)
        .where(PairingSession.code_hash == hash_secret(code))
        .with_for_update()
    )
    if pairing is None:
        raise PairingRejected("Invalid, expired, or already-used pairing code")
    if pairing.status != "pending" or _aware(pairing.expires_at) <= now:
        if pairing.status == "pending":
            pairing.status = "expired"
            session.commit()
        raise PairingRejected("Invalid, expired, or already-used pairing code")
    pairing.status = "approved"
    pairing.approved_at = now
    session.commit()
    return pairing.id


def pairing_status(
    session: Session, session_id: UUID, claim_secret: str, *, now: datetime
) -> str:
    pairing = _verified_session(session, session_id, claim_secret)
    if pairing.status in {"pending", "approved"} and _aware(pairing.expires_at) <= now:
        pairing.status = "expired"
        session.commit()
    return pairing.status


def claim_credential(
    session: Session, session_id: UUID, claim_secret: str, *, now: datetime
) -> str:
    pairing = _verified_session(session, session_id, claim_secret, lock=True)
    if pairing.status != "approved" or _aware(pairing.expires_at) <= now:
        if pairing.status == "approved" and _aware(pairing.expires_at) <= now:
            pairing.status = "expired"
            session.commit()
        raise PairingRejected("Pairing session is not claimable")
    public_id = secrets.token_urlsafe(12)
    secret = secrets.token_urlsafe(32)
    session.execute(
        update(DeviceCredential)
        .where(
            DeviceCredential.device_id == pairing.device_id,
            DeviceCredential.status == "active",
        )
        .values(status="revoked", revoked_at=now)
    )
    session.add(
        DeviceCredential(
            device_id=pairing.device_id,
            credential_id=public_id,
            secret_hash=hash_secret(secret),
            status="active",
            created_at=now,
        )
    )
    pairing.status = "consumed"
    pairing.consumed_at = now
    pairing.device.status = "active"
    pairing.device.paired_at = now
    pairing.device.revoked_at = None
    session.commit()
    LOGGER.info("audit event=device_paired device_id_prefix=%s", str(pairing.device.device_id)[:8])
    return f"device_{public_id}.{secret}"


def revoke_device(session: Session, device_uuid: UUID, *, now: datetime) -> bool:
    device = session.scalar(select(Device).where(Device.device_id == device_uuid))
    if device is None:
        return False
    device.status = "revoked"
    device.revoked_at = now
    session.execute(
        update(DeviceCredential)
        .where(DeviceCredential.device_id == device.id, DeviceCredential.status == "active")
        .values(status="revoked", revoked_at=now)
    )
    session.commit()
    LOGGER.info("audit event=device_revoked device_id_prefix=%s", str(device_uuid)[:8])
    return True


def _verified_session(
    session: Session, session_id: UUID, claim_secret: str, *, lock: bool = False
) -> PairingSession:
    statement = select(PairingSession).where(PairingSession.id == session_id)
    if lock:
        statement = statement.with_for_update()
    pairing = session.scalar(statement)
    if pairing is None or not hmac.compare_digest(
        pairing.claim_secret_hash, hash_secret(claim_secret)
    ):
        raise PairingRejected("Pairing session not found")
    return pairing
