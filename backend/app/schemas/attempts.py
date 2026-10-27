"""Exact Phase 9A attempt upload request and acknowledgement schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProfilePayload(StrictModel):
    local_profile_id: str = Field(min_length=1, max_length=255)
    server_user_id: str | None = Field(default=None, min_length=1, max_length=255)


class MarkingPayload(StrictModel):
    correct: float
    wrong: float
    skip: float


class QuestionSetPayload(StrictModel):
    set_id: str = Field(min_length=1, max_length=255)
    set_version: int = Field(ge=1)
    marking: MarkingPayload


class ResultPayload(StrictModel):
    score: float


class ResponsePayload(StrictModel):
    response_id: str = Field(min_length=1, max_length=255)
    question_id: str = Field(min_length=1, max_length=255)
    selected_key: Literal["A", "B", "C", "D"] | None
    confidence: Literal["sure", "not_sure", "guessing", "unrated"] | None
    is_correct: bool | None
    response_time_ms: int = Field(ge=0)
    marked_review: bool
    first_shown_at: datetime | None
    answered_at: datetime | None

    @model_validator(mode="after")
    def validate_answer_state(self) -> "ResponsePayload":
        if self.selected_key is None and (self.confidence is not None or self.is_correct is not None):
            raise ValueError("a skipped response cannot have confidence or correctness")
        if self.selected_key is not None and (self.confidence is None or self.is_correct is None):
            raise ValueError("an answered response requires confidence and correctness")
        return self


class AttemptUpload(StrictModel):
    payload_version: Literal[1]
    attempt_id: UUID
    device_id: str | None = Field(default=None, min_length=1, max_length=255)
    profile: ProfilePayload
    question_set: QuestionSetPayload
    started_at: datetime
    completed_at: datetime
    duration_ms: int = Field(ge=0)
    result: ResultPayload
    responses: list[ResponsePayload] = Field(min_length=1)

    @field_validator("started_at", "completed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must include a UTC offset")
        return value

    @model_validator(mode="after")
    def validate_timeline(self) -> "AttemptUpload":
        if self.completed_at < self.started_at:
            raise ValueError("completed_at must not precede started_at")
        return self


class AttemptAcknowledgement(StrictModel):
    status: Literal["accepted", "synced"]
    attempt_id: str
    code: Literal["accepted", "already_uploaded"]
