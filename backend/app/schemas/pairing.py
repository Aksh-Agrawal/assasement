"""Public pairing API shapes; hashes and internal identifiers never leave the API."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PairingRequestBody(BaseModel):
    device_id: UUID
    device_name: str | None = Field(default=None, max_length=255)


class PairingRequestResponse(BaseModel):
    session_id: UUID
    pairing_code: str
    claim_secret: str
    expires_at: datetime


class PairingStatusResponse(BaseModel):
    status: Literal["pending", "approved", "expired", "consumed"]


class CredentialResponse(BaseModel):
    credential: str
