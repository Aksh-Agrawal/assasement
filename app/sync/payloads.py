"""Deterministic upload payload construction from authoritative SQLite data."""

from typing import Any

from app.core.models import AttemptStatus
from app.data.db import datetime_to_text
from app.data.repo import Repository, UnknownAttempt

PAYLOAD_VERSION = 1


def _timestamp(value) -> str | None:
    return datetime_to_text(value) if value is not None else None


def build_upload_payload(repository: Repository, attempt_id: str) -> dict[str, Any]:
    """Build a stable versioned payload without generating IDs or timestamps."""
    attempt = repository.get_attempt(attempt_id)
    if attempt is None:
        raise UnknownAttempt(f"Unknown attempt {attempt_id!r}")
    if attempt.status is not AttemptStatus.COMPLETED:
        raise ValueError("Only completed attempts can be uploaded")

    question_set = repository.get_question_set(attempt.set_id, attempt.set_version)
    if question_set is None:
        raise ValueError("Attempt references a missing question-set version")
    profile = repository.get_profile(attempt.profile_id)
    if profile is None:
        raise ValueError("Attempt references a missing profile")

    response_items = []
    for response in repository.get_attempt_responses(attempt.id):
        persisted = repository.get_response_persistence(attempt.id, response.question_id)
        if persisted is None:
            raise ValueError(f"Response {response.id!r} has no persistence metadata")
        response_items.append(
            {
                "response_id": response.id,
                "question_id": response.question_id,
                "selected_key": response.selected_key,
                "confidence": response.confidence.value if response.confidence else None,
                "is_correct": persisted.is_correct,
                "response_time_ms": response.response_time_ms,
                "marked_review": response.marked_review,
                "first_shown_at": _timestamp(persisted.first_shown_at),
                "answered_at": _timestamp(persisted.answered_at),
            }
        )

    metadata = repository.get_schema_meta()
    device_id = metadata.get("device_id") or None
    return {
        "payload_version": PAYLOAD_VERSION,
        "attempt_id": attempt.id,
        "device_id": device_id,
        "profile": {
            "local_profile_id": profile.id,
            "server_user_id": profile.server_user_id,
        },
        "question_set": {
            "set_id": attempt.set_id,
            "set_version": attempt.set_version,
            "marking": {
                "correct": question_set.marking.correct,
                "wrong": question_set.marking.wrong,
                "skip": question_set.marking.skip,
            },
        },
        "started_at": _timestamp(attempt.started_at),
        "completed_at": _timestamp(attempt.completed_at),
        "duration_ms": attempt.duration_ms,
        "result": {"score": attempt.score},
        "responses": response_items,
    }
