"""Shared database and authenticated-device FastAPI dependencies."""

import hmac
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import Device, DeviceCredential
from backend.app.services.pairing import hash_secret

bearer = HTTPBearer(auto_error=False)


def database_session(request: Request):
    with request.app.state.session_factory() as session:
        yield session


@dataclass(frozen=True, slots=True)
class AuthenticatedDevice:
    database_id: int
    device_id: str


def authenticate_device(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: Annotated[Session, Depends(database_session)],
) -> AuthenticatedDevice:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Device credential required")
    token = credentials.credentials
    try:
        identifier, secret = token.removeprefix("device_").split(".", 1)
        if not token.startswith("device_") or not identifier or not secret:
            raise ValueError
    except ValueError as error:
        raise HTTPException(status_code=401, detail="Invalid device credential") from error
    row = session.execute(
        select(DeviceCredential, Device)
        .join(Device, Device.id == DeviceCredential.device_id)
        .where(DeviceCredential.credential_id == identifier)
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid device credential")
    credential, device = row
    if credential.status != "active" or device.status != "active" or not hmac.compare_digest(
        credential.secret_hash, hash_secret(secret)
    ):
        raise HTTPException(status_code=401, detail="Invalid device credential")
    now = datetime.now(UTC)
    credential.last_used_at = now
    device.last_seen_at = now
    session.commit()
    return AuthenticatedDevice(database_id=device.id, device_id=str(device.device_id))
