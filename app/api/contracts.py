"""Version 1 wire contracts, independent of server frameworks and persistence."""

from typing import Literal, TypedDict

from app.auth.pairing import PairingRequest as PairingStartResponse
from app.content.catalog import ContentCatalog, RemotePack
from app.update.client import AvailableUpdate as SoftwareUpdateMetadata

__all__ = ["PairingStartResponse", "ContentCatalog", "RemotePack", "SoftwareUpdateMetadata"]


class PairingStartRequest(TypedDict):
    device_id: str
    device_name: str | None


class PairingStatusResponse(TypedDict):
    status: Literal["pending", "approved", "expired", "consumed", "denied"]


class DeviceAuthenticationResponse(TypedDict):
    credential: str


class DownloadMetadata(TypedDict):
    set_id: str
    version: int
    size_bytes: int
    sha256: str
    download_reference: str


class Marking(TypedDict):
    correct: float
    wrong: float
    skip: float


class AttemptProfile(TypedDict):
    local_profile_id: str
    server_user_id: str | None


class AttemptQuestionSet(TypedDict):
    set_id: str
    set_version: int
    marking: Marking


class AttemptResult(TypedDict):
    score: float


class AttemptResponse(TypedDict):
    response_id: str
    question_id: str
    selected_key: Literal["A", "B", "C", "D"] | None
    confidence: Literal["sure", "not_sure", "guessing", "unrated"] | None
    is_correct: bool | None
    response_time_ms: int
    marked_review: bool
    first_shown_at: str | None
    answered_at: str | None


class AttemptUpload(TypedDict):
    payload_version: Literal[1]
    attempt_id: str
    device_id: str | None
    profile: AttemptProfile
    question_set: AttemptQuestionSet
    started_at: str
    completed_at: str
    duration_ms: int
    result: AttemptResult
    responses: list[AttemptResponse]


class SyncAcknowledgement(TypedDict):
    status: Literal["accepted", "synced"]
    attempt_id: str
    code: Literal["accepted", "already_uploaded"]


class HeartbeatAcknowledgement(TypedDict):
    status: Literal["accepted"]
