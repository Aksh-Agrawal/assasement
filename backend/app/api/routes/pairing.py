"""Public pairing request/status/claim routes."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from backend.app.api.dependencies import database_session
from backend.app.schemas.pairing import (
    CredentialResponse,
    PairingRequestBody,
    PairingRequestResponse,
    PairingStatusResponse,
)
from backend.app.services.pairing import (
    PairingRejected,
    claim_credential,
    pairing_status,
    request_pairing,
)

router = APIRouter(prefix="/api/v1/pairing", tags=["pairing"])


def _now(request: Request) -> datetime:
    return request.app.state.clock()


@router.post("/request", response_model=PairingRequestResponse, status_code=201)
def create_pairing(
    body: PairingRequestBody,
    request: Request,
    session: Annotated[Session, Depends(database_session)],
) -> PairingRequestResponse:
    result = request_pairing(
        session,
        body.device_id,
        body.device_name,
        now=_now(request),
        ttl_seconds=request.app.state.settings.pairing_code_ttl_seconds,
    )
    return PairingRequestResponse(
        session_id=result.session_id,
        pairing_code=result.code,
        claim_secret=result.claim_secret,
        expires_at=result.expires_at,
    )


@router.get("/{session_id}/status", response_model=PairingStatusResponse)
def get_pairing_status(
    session_id: UUID,
    request: Request,
    session: Annotated[Session, Depends(database_session)],
    claim: Annotated[str, Header(alias="X-Pairing-Claim")],
) -> PairingStatusResponse:
    try:
        state = pairing_status(session, session_id, claim, now=_now(request))
    except PairingRejected as error:
        raise HTTPException(status_code=404, detail="Pairing session not found") from error
    return PairingStatusResponse(status=state)


@router.post("/{session_id}/claim", response_model=CredentialResponse)
def claim_pairing(
    session_id: UUID,
    request: Request,
    session: Annotated[Session, Depends(database_session)],
    claim: Annotated[str, Header(alias="X-Pairing-Claim")],
) -> CredentialResponse:
    try:
        token = claim_credential(session, session_id, claim, now=_now(request))
    except PairingRejected as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return CredentialResponse(credential=token)
