"""Safe publication and resolution of immutable question-pack artifacts."""

import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.validator import ValidatedPack, validate_pack_bytes
from backend.app.db.models import QuestionPack

LOGGER = logging.getLogger(__name__)


class PackVersionConflict(ValueError):
    """The canonical set/version already points at different exact bytes."""


@dataclass(frozen=True, slots=True)
class PublishResult:
    pack: QuestionPack
    created: bool


def _artifact_name(validated: ValidatedPack) -> str:
    question_set = validated.question_set
    return f"{question_set.id}-v{question_set.version}-{validated.sha256}.json"


def resolve_storage_path(storage_root: Path, storage_name: str) -> Path:
    """Resolve only a server-generated basename beneath the configured root."""
    if not storage_name or storage_name != Path(storage_name).name:
        raise ValueError("Unsafe content storage path")
    root = storage_root.resolve()
    candidate = (root / storage_name).resolve()
    if candidate.parent != root:
        raise ValueError("Unsafe content storage path")
    return candidate


def publish_pack_bytes(
    data: bytes,
    *,
    session: Session,
    storage_root: Path,
    now: datetime | None = None,
) -> PublishResult:
    """Validate, store exact bytes, then transactionally publish immutable metadata."""
    validated = validate_pack_bytes(data)
    question_set = validated.question_set
    existing = session.scalar(
        select(QuestionPack).where(
            QuestionPack.set_id == question_set.id,
            QuestionPack.version == question_set.version,
        )
    )
    if existing is not None:
        if existing.sha256 != validated.sha256 or existing.size_bytes != len(data):
            raise PackVersionConflict(
                f"{question_set.id} version {question_set.version} is already published "
                "with different bytes"
            )
        return PublishResult(existing, created=False)

    storage_root.mkdir(parents=True, exist_ok=True)
    storage_name = _artifact_name(validated)
    destination = resolve_storage_path(storage_root, storage_name)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".publish-", dir=storage_root)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, destination)
        timestamp = now or datetime.now(UTC)
        row = QuestionPack(
            set_id=question_set.id,
            version=question_set.version,
            title=question_set.title,
            subject=question_set.subject,
            chapter=question_set.chapter,
            schema_version=validated.schema_version,
            question_count=len(question_set.questions),
            sha256=validated.sha256,
            size_bytes=len(data),
            storage_path=storage_name,
            is_active=True,
            published_at=timestamp,
            created_at=timestamp,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        LOGGER.info(
            "audit event=pack_published set_id=%s version=%d sha256_prefix=%s",
            row.set_id,
            row.version,
            row.sha256[:12],
        )
        return PublishResult(row, created=True)
    except Exception:
        session.rollback()
        if destination.exists():
            destination.unlink()
        raise
    finally:
        temporary.unlink(missing_ok=True)


def publish_pack_file(
    path: Path, *, session: Session, storage_root: Path, now: datetime | None = None
) -> PublishResult:
    return publish_pack_bytes(path.read_bytes(), session=session, storage_root=storage_root, now=now)
