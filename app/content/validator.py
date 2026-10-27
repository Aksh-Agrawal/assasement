"""Schema, semantic, integrity, and domain validation for local pack bytes."""

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Any, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from app.content.hashing import sha256_bytes
from app.core.models import MarkingScheme, Option, OptionKey, Question, QuestionSet

SUPPORTED_SCHEMA_VERSION = 1
DEFAULT_MAX_PACK_BYTES = 25 * 1024 * 1024
DEFAULT_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "pack.schema.json"
OPTION_KEYS = ("A", "B", "C", "D")


class PackErrorCode(StrEnum):
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    INVALID_UTF8 = "INVALID_UTF8"
    INVALID_JSON = "INVALID_JSON"
    SCHEMA_ERROR = "SCHEMA_ERROR"
    UNSUPPORTED_SCHEMA_VERSION = "UNSUPPORTED_SCHEMA_VERSION"
    DUPLICATE_QUESTION_ID = "DUPLICATE_QUESTION_ID"
    DUPLICATE_POSITION = "DUPLICATE_POSITION"
    INVALID_POSITION_SEQUENCE = "INVALID_POSITION_SEQUENCE"
    INVALID_OPTION_KEYS = "INVALID_OPTION_KEYS"
    INVALID_CORRECT_KEY = "INVALID_CORRECT_KEY"
    EMPTY_REQUIRED_TEXT = "EMPTY_REQUIRED_TEXT"
    EMPTY_QUESTION_TEXT = "EMPTY_QUESTION_TEXT"
    INVALID_MEDIA_REF = "INVALID_MEDIA_REF"
    HASH_MISMATCH = "HASH_MISMATCH"
    DOMAIN_ERROR = "DOMAIN_ERROR"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: PackErrorCode
    path: str
    message: str


class PackValidationError(ValueError):
    """One or more structured validation failures."""

    def __init__(self, issues: list[ValidationIssue] | tuple[ValidationIssue, ...]) -> None:
        self.issues = tuple(issues)
        if not self.issues:
            raise ValueError("PackValidationError requires at least one issue")
        first = self.issues[0]
        super().__init__(f"[{first.code}] {first.path}: {first.message}")


@dataclass(frozen=True, slots=True)
class PackSummary:
    set_id: str
    version: int
    title: str
    subject: str
    chapter: str
    questions: int
    sha256: str


@dataclass(frozen=True, slots=True)
class ValidatedPack:
    question_set: QuestionSet
    sha256: str
    schema_version: int

    @property
    def summary(self) -> PackSummary:
        question_set = self.question_set
        return PackSummary(
            set_id=question_set.id,
            version=question_set.version,
            title=question_set.title,
            subject=question_set.subject,
            chapter=question_set.chapter,
            questions=len(question_set.questions),
            sha256=self.sha256,
        )


def _issue(code: PackErrorCode, path: str, message: str) -> PackValidationError:
    return PackValidationError([ValidationIssue(code=code, path=path, message=message)])


def _json_path(parts: object) -> str:
    result = ""
    for part in parts:  # type: ignore[union-attr]
        if isinstance(part, int):
            result += f"[{part}]"
        else:
            result += ("." if result else "") + str(part)
    return result or "$"


def _schema_issue(error: ValidationError) -> ValidationIssue:
    path = _json_path(error.absolute_path)
    if path == "schema_version":
        code = PackErrorCode.UNSUPPORTED_SCHEMA_VERSION
    elif ".options" in path or path.endswith("options"):
        code = PackErrorCode.INVALID_OPTION_KEYS
    elif path.endswith("correct_key"):
        code = PackErrorCode.INVALID_CORRECT_KEY
    elif path.endswith("question_text") and error.validator == "minLength":
        code = PackErrorCode.EMPTY_QUESTION_TEXT
    else:
        code = PackErrorCode.SCHEMA_ERROR
    return ValidationIssue(code=code, path=path, message=error.message)


def _load_schema(schema_path: Path) -> dict[str, Any]:
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
    except (OSError, UnicodeError, json.JSONDecodeError, SchemaError) as error:
        raise RuntimeError(f"Invalid installed pack schema {schema_path}: {error}") from error
    return cast(dict[str, Any], schema)


def _parse_json(data: bytes) -> Any:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise _issue(
            PackErrorCode.INVALID_UTF8,
            "$",
            f"Pack is not valid UTF-8 at byte {error.start}",
        ) from error
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise _issue(
            PackErrorCode.INVALID_JSON,
            "$",
            f"Invalid JSON at line {error.lineno}, column {error.colno}: {error.msg}",
        ) from error


def _is_safe_media_ref(value: str) -> bool:
    if not value or value != value.strip() or "\\" in value or "\x00" in value:
        return False
    if re.match(r"^[A-Za-z]:", value):
        return False
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value:
        return False
    parts = path.parts
    return (
        len(parts) >= 2
        and parts[0] == "media"
        and all(part not in {"", ".", ".."} and ":" not in part for part in parts)
    )


def _semantic_issues(pack: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    metadata = pack["set"]
    for field in ("id", "title", "subject", "chapter"):
        if not metadata[field].strip():
            issues.append(
                ValidationIssue(
                    PackErrorCode.EMPTY_REQUIRED_TEXT,
                    f"set.{field}",
                    f"Set {field} must not be blank",
                )
            )

    seen_ids: dict[str, int] = {}
    seen_positions: dict[int, int] = {}
    for index, question in enumerate(pack["questions"]):
        question_id = question["id"]
        if question_id in seen_ids:
            issues.append(
                ValidationIssue(
                    PackErrorCode.DUPLICATE_QUESTION_ID,
                    f"questions[{index}].id",
                    f"Duplicate question ID {question_id!r}; first used at index "
                    f"{seen_ids[question_id]}",
                )
            )
        else:
            seen_ids[question_id] = index

        position = question["position"]
        if position in seen_positions:
            issues.append(
                ValidationIssue(
                    PackErrorCode.DUPLICATE_POSITION,
                    f"questions[{index}].position",
                    f"Duplicate position {position}; first used at index "
                    f"{seen_positions[position]}",
                )
            )
        else:
            seen_positions[position] = index

        if not question["question_text"].strip():
            issues.append(
                ValidationIssue(
                    PackErrorCode.EMPTY_QUESTION_TEXT,
                    f"questions[{index}].question_text",
                    "Question text must not be blank",
                )
            )
        for field in ("id", "topic"):
            if not question[field].strip():
                issues.append(
                    ValidationIssue(
                        PackErrorCode.EMPTY_REQUIRED_TEXT,
                        f"questions[{index}].{field}",
                        f"Question {field} must not be blank",
                    )
                )
        explanation = question.get("explanation")
        if explanation is not None and not explanation.strip():
            issues.append(
                ValidationIssue(
                    PackErrorCode.EMPTY_REQUIRED_TEXT,
                    f"questions[{index}].explanation",
                    "Explanation must not be blank when present",
                )
            )

        options = question["options"]
        keys = tuple(option["key"] for option in options)
        if keys != OPTION_KEYS:
            issues.append(
                ValidationIssue(
                    PackErrorCode.INVALID_OPTION_KEYS,
                    f"questions[{index}].options",
                    f"Option keys must be exactly {OPTION_KEYS!r} in order; got {keys!r}",
                )
            )
        for option_index, option in enumerate(options):
            if not option["text"].strip():
                issues.append(
                    ValidationIssue(
                        PackErrorCode.EMPTY_REQUIRED_TEXT,
                        f"questions[{index}].options[{option_index}].text",
                        "Option text must not be blank",
                    )
                )
        if question["correct_key"] not in keys:
            issues.append(
                ValidationIssue(
                    PackErrorCode.INVALID_CORRECT_KEY,
                    f"questions[{index}].correct_key",
                    f"Correct key {question['correct_key']!r} is not an actual option",
                )
            )
        media_ref = question["media_ref"]
        if media_ref is not None and not _is_safe_media_ref(media_ref):
            issues.append(
                ValidationIssue(
                    PackErrorCode.INVALID_MEDIA_REF,
                    f"questions[{index}].media_ref",
                    "Media reference must be a normalized relative path below media/",
                )
            )

    positions = set(seen_positions)
    expected_positions = set(range(1, len(pack["questions"]) + 1))
    if positions != expected_positions and not any(
        issue.code is PackErrorCode.DUPLICATE_POSITION for issue in issues
    ):
        issues.append(
            ValidationIssue(
                PackErrorCode.INVALID_POSITION_SEQUENCE,
                "questions",
                f"Positions must be contiguous from 1 through {len(pack['questions'])}",
            )
        )
    return issues


def _to_domain(pack: dict[str, Any]) -> QuestionSet:
    metadata = pack["set"]
    marking = metadata["marking"]
    questions = tuple(
        Question(
            id=item["id"],
            position=item["position"],
            topic=item["topic"],
            difficulty=item["difficulty"],
            question_text=item["question_text"],
            options=tuple(
                Option(key=cast(OptionKey, option["key"]), text=option["text"])
                for option in item["options"]
            ),
            correct_key=cast(OptionKey, item["correct_key"]),
            explanation=item.get("explanation"),
            media_ref=item["media_ref"],
        )
        for item in pack["questions"]
    )
    return QuestionSet(
        id=metadata["id"],
        version=metadata["version"],
        title=metadata["title"],
        subject=metadata["subject"],
        chapter=metadata["chapter"],
        marking=MarkingScheme(
            correct=marking["correct"], wrong=marking["wrong"], skip=marking["skip"]
        ),
        questions=questions,
    )


def validate_pack_bytes(
    data: bytes,
    *,
    expected_sha256: str | None = None,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    max_bytes: int = DEFAULT_MAX_PACK_BYTES,
) -> ValidatedPack:
    """Validate exact local/downloaded bytes without performing database writes."""
    if max_bytes < 1:
        raise ValueError("max_bytes must be positive")
    if len(data) > max_bytes:
        raise _issue(
            PackErrorCode.FILE_TOO_LARGE,
            "$",
            f"Pack has {len(data)} bytes; configured maximum is {max_bytes}",
        )
    parsed = _parse_json(data)
    schema = _load_schema(schema_path)
    schema_errors = sorted(
        Draft202012Validator(schema).iter_errors(parsed),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if schema_errors:
        raise PackValidationError([_schema_issue(error) for error in schema_errors])

    pack = cast(dict[str, Any], parsed)
    semantic_issues = _semantic_issues(pack)
    if semantic_issues:
        raise PackValidationError(semantic_issues)

    actual_sha256 = sha256_bytes(data)
    if expected_sha256 is not None and actual_sha256 != expected_sha256.lower():
        raise _issue(
            PackErrorCode.HASH_MISMATCH,
            "$",
            f"Expected SHA-256 {expected_sha256.lower()}, got {actual_sha256}",
        )
    try:
        question_set = _to_domain(pack)
    except (TypeError, ValueError) as error:
        raise _issue(PackErrorCode.DOMAIN_ERROR, "$", str(error)) from error
    return ValidatedPack(
        question_set=question_set,
        sha256=actual_sha256,
        schema_version=pack["schema_version"],
    )


def validate_pack(
    path: Path,
    *,
    expected_sha256: str | None = None,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    max_bytes: int = DEFAULT_MAX_PACK_BYTES,
) -> ValidatedPack:
    """Read and validate one UTF-8 JSON file with a configurable size guard."""
    try:
        size = path.stat().st_size
    except OSError as error:
        raise _issue(PackErrorCode.INVALID_JSON, "$", f"Cannot read pack: {error}") from error
    if size > max_bytes:
        raise _issue(
            PackErrorCode.FILE_TOO_LARGE,
            "$",
            f"Pack has {size} bytes; configured maximum is {max_bytes}",
        )
    try:
        data = path.read_bytes()
    except OSError as error:
        raise _issue(PackErrorCode.INVALID_JSON, "$", f"Cannot read pack: {error}") from error
    return validate_pack_bytes(
        data,
        expected_sha256=expected_sha256,
        schema_path=schema_path,
        max_bytes=max_bytes,
    )
