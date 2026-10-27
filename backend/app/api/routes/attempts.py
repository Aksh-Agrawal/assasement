"""Authenticated attempt upload route."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.api.dependencies import (
    AuthenticatedDevice,
    authenticate_device,
    database_session,
)
from backend.app.schemas.attempts import AttemptAcknowledgement, AttemptUpload
from backend.app.services.attempts import ConflictingAttempt, InvalidAttempt, store_attempt

router = APIRouter(prefix="/api/v1")


@router.put(
    "/attempts/{attempt_id}",
    response_model=AttemptAcknowledgement,
    status_code=status.HTTP_201_CREATED,
)
def upload_attempt(
    attempt_id: str,
    payload: AttemptUpload,
    session: Annotated[Session, Depends(database_session)],
    device: Annotated[AuthenticatedDevice, Depends(authenticate_device)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    payload_version: Annotated[str | None, Header(alias="X-Attempt-Payload-Version")] = None,
) -> AttemptAcknowledgement:
    body_id = str(payload.attempt_id)
    if attempt_id != body_id or idempotency_key != body_id:
        raise HTTPException(status_code=400, detail="path, body, and idempotency identities must match")
    if payload_version != str(payload.payload_version):
        raise HTTPException(status_code=400, detail="payload version header does not match body")
    try:
        result = store_attempt(session, payload, device)
    except ConflictingAttempt as error:
        raise HTTPException(
            status_code=409,
            detail={"code": "attempt_conflict", "attempt_id": body_id},
        ) from error
    except InvalidAttempt as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except SQLAlchemyError as error:
        session.rollback()
        raise HTTPException(status_code=503, detail="Backend database unavailable") from error
    if result.already_uploaded:
        return AttemptAcknowledgement(
            status="synced", attempt_id=body_id, code="already_uploaded"
        )
    return AttemptAcknowledgement(status="accepted", attempt_id=body_id, code="accepted")
