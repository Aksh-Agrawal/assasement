"""Validated, exact-byte-hashed, atomic question-pack installation."""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.content.validator import DEFAULT_MAX_PACK_BYTES, ValidatedPack, validate_pack
from app.data.repo import DuplicateQuestionSetVersion, Repository


class PackImportError(RuntimeError):
    """Structured import failure after content validation succeeded."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


@dataclass(frozen=True, slots=True)
class ImportResult:
    pack: ValidatedPack
    imported_at: datetime
    active: bool


def import_pack(
    path: Path,
    repository: Repository,
    *,
    expected_sha256: str | None = None,
    make_active: bool = True,
    max_bytes: int = DEFAULT_MAX_PACK_BYTES,
    now: datetime | None = None,
    profile_only: bool = False,
) -> ImportResult:
    """Fully validate before calling the repository's single atomic import."""
    validated = validate_pack(
        path,
        expected_sha256=expected_sha256,
        max_bytes=max_bytes,
    )
    imported_at = now or datetime.now(UTC)
    if imported_at.tzinfo is None or imported_at.utcoffset() is None:
        raise ValueError("Import timestamp must be timezone-aware")
    try:
        repository.import_question_set(
            validated.question_set,
            content_hash=validated.sha256,
            downloaded_at=imported_at,
            is_active=make_active,
            profile_only=profile_only,
        )
    except DuplicateQuestionSetVersion as error:
        raise PackImportError(
            "DUPLICATE_SET_VERSION",
            f"Question set {validated.question_set.id!r} version "
            f"{validated.question_set.version} is already installed",
        ) from error
    return ImportResult(pack=validated, imported_at=imported_at, active=make_active)
