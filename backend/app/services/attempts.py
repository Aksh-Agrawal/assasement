"""Transactional attempt creation and deterministic idempotency."""

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.api.dependencies import AuthenticatedDevice
from backend.app.db.models import Attempt, AttemptResponse
from backend.app.schemas.attempts import AttemptUpload


class ConflictingAttempt(RuntimeError):
    pass


class InvalidAttempt(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class StoreResult:
    attempt: Attempt
    already_uploaded: bool


def payload_fingerprint(payload: AttemptUpload) -> str:
    """SHA-256 of every request-body field as sorted, compact canonical JSON."""
    canonical = json.dumps(
        payload.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def store_attempt(
    session: Session, payload: AttemptUpload, authenticated_device: AuthenticatedDevice
) -> StoreResult:
    external_id = payload.attempt_id
    fingerprint = payload_fingerprint(payload)
    existing = session.scalar(select(Attempt).where(Attempt.device_attempt_id == external_id))
    if existing is not None:
        if (
            existing.authenticated_device_id != authenticated_device.database_id
            or existing.payload_hash != fingerprint
        ):
            raise ConflictingAttempt(str(external_id))
        return StoreResult(existing, already_uploaded=True)

    question_set = payload.question_set
    profile = payload.profile
    attempt = Attempt(
        device_attempt_id=external_id,
        authenticated_device_id=authenticated_device.database_id,
        payload_version=payload.payload_version,
        device_id=authenticated_device.device_id,
        profile_id=profile.local_profile_id,
        server_user_id=profile.server_user_id,
        question_set_id=question_set.set_id,
        question_set_version=question_set.set_version,
        marking_correct=question_set.marking.correct,
        marking_wrong=question_set.marking.wrong,
        marking_skip=question_set.marking.skip,
        started_at=payload.started_at,
        completed_at=payload.completed_at,
        duration_ms=payload.duration_ms,
        score=payload.result.score,
        payload_hash=fingerprint,
        created_at=datetime.now(UTC),
    )
    attempt.responses = [
        AttemptResponse(
            device_response_id=item.response_id,
            question_id=item.question_id,
            selected_key=item.selected_key,
            confidence=item.confidence,
            is_correct=item.is_correct,
            response_time_ms=item.response_time_ms,
            marked_review=item.marked_review,
            first_shown_at=item.first_shown_at,
            answered_at=item.answered_at,
        )
        for item in payload.responses
    ]
    try:
        with session.begin_nested():
            session.add(attempt)
            session.flush()
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raced = session.scalar(select(Attempt).where(Attempt.device_attempt_id == external_id))
        if raced is not None:
            if (
                raced.authenticated_device_id == authenticated_device.database_id
                and raced.payload_hash == fingerprint
            ):
                return StoreResult(raced, already_uploaded=True)
            raise ConflictingAttempt(str(external_id)) from error
        raise InvalidAttempt("attempt responses violate a database constraint") from error
    except Exception:
        session.rollback()
        raise
    return StoreResult(attempt, already_uploaded=False)
