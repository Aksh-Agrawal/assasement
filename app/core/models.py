"""Immutable, platform-independent assessment domain models."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from math import isfinite
from types import MappingProxyType
from typing import Literal, TypeAlias

OptionKey: TypeAlias = Literal["A", "B", "C", "D"]
Mark: TypeAlias = int | float

_OPTION_KEYS = ("A", "B", "C", "D")


def _require_text(name: str, value: str) -> None:
    if not value.strip():
        raise ValueError(f"{name} must not be empty")


def _require_mark(name: str, value: Mark) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{name} must be a finite number")


def _require_non_negative_int(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")


class Confidence(StrEnum):
    """Stored student-confidence values from the Phase 0 contract."""

    SURE = "sure"
    NOT_SURE = "not_sure"
    GUESSING = "guessing"
    UNRATED = "unrated"


@dataclass(frozen=True, slots=True)
class Option:
    """One answer option for a single-correct question."""

    key: OptionKey
    text: str

    def __post_init__(self) -> None:
        if self.key not in _OPTION_KEYS:
            raise ValueError(f"Invalid option key {self.key!r}")
        _require_text("Option text", self.text)


@dataclass(frozen=True, slots=True)
class MarkingScheme:
    """Question-set-owned marks for correct, wrong, and skipped answers."""

    correct: Mark = 4
    wrong: Mark = -1
    skip: Mark = 0

    def __post_init__(self) -> None:
        _require_mark("Correct marks", self.correct)
        _require_mark("Wrong marks", self.wrong)
        _require_mark("Skip marks", self.skip)
        if self.correct <= 0:
            raise ValueError("Correct marks must be positive")
        if self.wrong > 0:
            raise ValueError("Wrong marks must be zero or negative")
        if self.skip > 0:
            raise ValueError("Skip marks must be zero or negative")


@dataclass(frozen=True, slots=True)
class Question:
    """A versioned-pack question containing everything needed for scoring."""

    id: str
    position: int
    topic: str
    difficulty: int
    question_text: str
    options: tuple[Option, ...]
    correct_key: OptionKey
    explanation: str | None = None
    media_ref: str | None = None

    def __post_init__(self) -> None:
        _require_text("Question ID", self.id)
        _require_text("Question topic", self.topic)
        _require_text("Question text", self.question_text)
        if (
            isinstance(self.position, bool)
            or not isinstance(self.position, int)
            or self.position < 1
        ):
            raise ValueError("Question position must be a positive integer")
        if (
            isinstance(self.difficulty, bool)
            or not isinstance(self.difficulty, int)
            or not 1 <= self.difficulty <= 5
        ):
            raise ValueError("Question difficulty must be between 1 and 5")

        options = tuple(self.options)
        object.__setattr__(self, "options", options)
        if any(not isinstance(option, Option) for option in options):
            raise ValueError("Question options must be Option values")
        keys = tuple(option.key for option in options)
        if keys != _OPTION_KEYS:
            raise ValueError("Question options must be ordered A, B, C, D")
        if self.correct_key not in keys:
            raise ValueError(f"Correct key {self.correct_key!r} is not an option")
        if self.explanation is not None:
            _require_text("Question explanation", self.explanation)
        if self.media_ref is not None:
            _require_text("Question media reference", self.media_ref)


@dataclass(frozen=True, slots=True)
class QuestionSet:
    """An immutable logical question-set version and its marking rules."""

    id: str
    version: int
    title: str
    subject: str
    chapter: str
    marking: MarkingScheme
    questions: tuple[Question, ...]

    def __post_init__(self) -> None:
        _require_text("Question-set ID", self.id)
        _require_text("Question-set title", self.title)
        _require_text("Question-set chapter", self.chapter)
        if (
            isinstance(self.version, bool)
            or not isinstance(self.version, int)
            or self.version < 1
        ):
            raise ValueError("Question-set version must be a positive integer")
        if self.subject not in {"Biology", "Chemistry"}:
            raise ValueError("Question-set subject must be Biology or Chemistry")

        questions = tuple(self.questions)
        object.__setattr__(self, "questions", questions)
        if not questions:
            raise ValueError("Question set must contain at least one question")
        if any(not isinstance(question, Question) for question in questions):
            raise ValueError("Question set entries must be Question values")
        if not isinstance(self.marking, MarkingScheme):
            raise ValueError("Question-set marking must be a MarkingScheme")
        question_ids = [question.id for question in questions]
        positions = [question.position for question in questions]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("Question IDs must be unique within a question set")
        if len(positions) != len(set(positions)):
            raise ValueError("Question positions must be unique within a question set")


@dataclass(frozen=True, slots=True)
class Profile:
    """Student identity data without authentication or persistence behavior."""

    id: str
    display_name: str
    server_user_id: str | None = None
    cloud_account_id: str | None = None
    cloud_profile_id: str | None = None
    ownership_state: str = "legacy_unclaimed"
    link_state: str = "unlinked"

    def __post_init__(self) -> None:
        _require_text("Profile ID", self.id)
        _require_text("Profile display name", self.display_name)
        if self.server_user_id is not None:
            _require_text("Server user ID", self.server_user_id)
        if self.ownership_state not in {"legacy_unclaimed", "owned"}:
            raise ValueError("Invalid profile ownership state")
        if self.link_state not in {"unlinked", "link_pending", "linked", "link_error"}:
            raise ValueError("Invalid profile link state")
        if self.ownership_state == "legacy_unclaimed":
            if self.cloud_account_id or self.cloud_profile_id or self.link_state != "unlinked":
                raise ValueError("Legacy profiles cannot imply cloud ownership")
        elif not self.cloud_account_id or not self.cloud_profile_id:
            raise ValueError("Owned profiles require cloud account and profile identifiers")



class AttemptStatus(StrEnum):
    """Coarse lifecycle status of an assessment attempt."""

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


@dataclass(frozen=True, slots=True)
class Attempt:
    """Platform-independent attempt metadata without storage or engine behavior."""

    id: str
    profile_id: str
    set_id: str
    set_version: int
    status: AttemptStatus = AttemptStatus.IN_PROGRESS
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int = 0
    score: Mark | None = None

    def __post_init__(self) -> None:
        _require_text("Attempt ID", self.id)
        _require_text("Attempt profile ID", self.profile_id)
        _require_text("Attempt set ID", self.set_id)
        if (
            isinstance(self.set_version, bool)
            or not isinstance(self.set_version, int)
            or self.set_version < 1
        ):
            raise ValueError("Attempt set version must be a positive integer")
        if not isinstance(self.status, AttemptStatus):
            raise ValueError("Attempt status must be an AttemptStatus")
        _require_non_negative_int("Attempt duration", self.duration_ms)
        if self.score is not None:
            _require_mark("Attempt score", self.score)


@dataclass(frozen=True, slots=True)
class Response:
    """The final current response for one attempt question."""

    id: str
    attempt_id: str
    question_id: str
    selected_key: OptionKey | None = None
    confidence: Confidence | None = None
    response_time_ms: int = 0
    marked_review: bool = False

    def __post_init__(self) -> None:
        _require_text("Response ID", self.id)
        _require_text("Response attempt ID", self.attempt_id)
        _require_text("Response question ID", self.question_id)
        if self.selected_key is not None and self.selected_key not in _OPTION_KEYS:
            raise ValueError(f"Invalid selected key {self.selected_key!r}")
        if self.confidence is not None and not isinstance(self.confidence, Confidence):
            raise ValueError("Response confidence must be a Confidence value")
        if self.selected_key is None and self.confidence is not None:
            raise ValueError("A skipped response cannot have confidence")
        if self.selected_key is not None and self.confidence is None:
            raise ValueError("An attempted response must store confidence, including unrated")
        _require_non_negative_int("Response time", self.response_time_ms)
        if not isinstance(self.marked_review, bool):
            raise ValueError("Response marked_review must be a boolean")


def _freeze_confidence_counts(
    name: str, values: Mapping[Confidence, int]
) -> Mapping[Confidence, int]:
    if any(not isinstance(key, Confidence) for key in values):
        raise ValueError(f"{name} keys must be Confidence values")
    if set(values) != set(Confidence):
        raise ValueError(f"{name} must contain every confidence bucket")
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in values.values()
    ):
        raise ValueError(f"{name} values must be non-negative integers")
    return MappingProxyType({bucket: values[bucket] for bucket in Confidence})


@dataclass(frozen=True, slots=True)
class ScoreResult:
    """Deterministic aggregate score and confidence analytics."""

    score: Mark
    correct: int
    wrong: int
    skipped: int
    attempted: int
    accuracy: float
    confidence_totals: Mapping[Confidence, int]
    confidence_correct: Mapping[Confidence, int]
    confidence_wrong: Mapping[Confidence, int]
    sure_but_wrong_question_ids: tuple[str, ...]
    guessed_right_question_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_mark("Score", self.score)
        for name in ("correct", "wrong", "skipped", "attempted"):
            value = getattr(self, name)
            _require_non_negative_int(name, value)
        if self.attempted != self.correct + self.wrong:
            raise ValueError("Attempted must equal correct plus wrong")
        if not isfinite(self.accuracy) or not 0.0 <= self.accuracy <= 1.0:
            raise ValueError("Accuracy must be between 0.0 and 1.0")

        totals = _freeze_confidence_counts("Confidence totals", self.confidence_totals)
        correct = _freeze_confidence_counts("Confidence correct", self.confidence_correct)
        wrong = _freeze_confidence_counts("Confidence wrong", self.confidence_wrong)
        for bucket in Confidence:
            if totals[bucket] != correct[bucket] + wrong[bucket]:
                raise ValueError(f"Confidence total mismatch for {bucket.value}")
        if sum(totals.values()) != self.attempted:
            raise ValueError("Confidence totals must sum to attempted")
        if sum(correct.values()) != self.correct:
            raise ValueError("Confidence correct counts must sum to correct")
        if sum(wrong.values()) != self.wrong:
            raise ValueError("Confidence wrong counts must sum to wrong")

        object.__setattr__(self, "confidence_totals", totals)
        object.__setattr__(self, "confidence_correct", correct)
        object.__setattr__(self, "confidence_wrong", wrong)
        object.__setattr__(
            self, "sure_but_wrong_question_ids", tuple(self.sure_but_wrong_question_ids)
        )
        object.__setattr__(
            self, "guessed_right_question_ids", tuple(self.guessed_right_question_ids)
        )

