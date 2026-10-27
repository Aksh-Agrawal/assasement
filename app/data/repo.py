"""SQLite repository mapping durable rows to Phase 2 domain models."""

import json
import logging
import sqlite3
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path

from app.core.models import (
    Attempt,
    AttemptStatus,
    Confidence,
    MarkingScheme,
    Option,
    Profile,
    Question,
    QuestionSet,
    Response,
)
from app.data.db import (
    IntegrityCheckResult,
    backup_database,
    check_integrity,
    connect_database,
    datetime_from_text,
    datetime_to_text,
    get_schema_version,
    quick_check,
    run_migrations,
    transaction,
    utc_now_text,
)
from app.faults import FaultHook, no_fault

LOGGER = logging.getLogger(__name__)


class RepositoryError(RuntimeError):
    """Base error for repository-level contract failures."""


class DuplicateQuestionSetVersion(RepositoryError):
    """Raised when immutable question-set content already exists."""


class UnknownQuestionSet(RepositoryError):
    """Raised when an exact question-set version does not exist."""


class UnknownAttempt(RepositoryError):
    """Raised when an attempt ID does not exist."""


class AttemptQuestionOrderAlreadyExists(RepositoryError):
    """Raised when code tries to replace a fixed attempt order."""


class DataIntegrityError(RepositoryError):
    """Raised when stored rows cannot form the promised domain object."""


class LocalDatabaseIntegrityError(RepositoryError):
    """Raised before normal use when SQLite reports corruption."""


class SyncStatus(StrEnum):
    """Persistence-only synchronization states; no networking behavior."""

    LOCAL = "local"
    PENDING = "pending"
    SYNCING = "syncing"
    SYNCED = "synced"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class AttemptSyncState:
    """Stored synchronization metadata associated with an attempt."""

    status: SyncStatus
    attempts: int
    last_error: str | None
    synced_at: datetime | None
    next_sync_at: datetime | None
    sync_started_at: datetime | None
    error_kind: str | None


@dataclass(frozen=True, slots=True)
class ResponsePersistence:
    """Data-layer response fields intentionally absent from core Response."""

    is_correct: bool | None
    first_shown_at: datetime | None
    answered_at: datetime | None


@dataclass(frozen=True, slots=True)
class QuestionSetPersistence:
    """Installation metadata kept outside the pure question-set model."""

    content_hash: str
    downloaded_at: datetime
    is_active: bool


@dataclass(frozen=True, slots=True)
class ResponseEvent:
    """One append-only response history event."""

    id: str
    attempt_id: str
    question_id: str
    event_type: str
    value: str | None
    at_ms: int
    at_utc: datetime


class Repository:
    """Own one explicitly managed SQLite connection and repository API."""

    def __init__(
        self,
        database_path: Path,
        *,
        device_id: str | None = None,
        fault_hook: FaultHook = no_fault,
    ) -> None:
        try:
            self._connection = connect_database(database_path)
        except sqlite3.DatabaseError as error:
            LOGGER.error("local database open/integrity failure path=%s", database_path)
            raise LocalDatabaseIntegrityError("LOCAL_DATABASE_ERROR") from error
        self._fault_hook = fault_hook
        self._closed = False
        try:
            integrity = check_integrity(self._connection)
            if not integrity.ok:
                LOGGER.error("local database integrity check failed path=%s", database_path)
                raise LocalDatabaseIntegrityError(
                    "LOCAL_DATABASE_ERROR: " + "; ".join(integrity.messages)
                )
            run_migrations(self._connection)
            if device_id is not None:
                self.set_schema_meta("device_id", device_id)
            else:
                self.get_or_create_device_id()
            LOGGER.info("local database opened path=%s schema_version=%d", database_path, self.schema_version)
        except sqlite3.DatabaseError as error:
            self._connection.close()
            self._closed = True
            LOGGER.error("local database startup failure path=%s", database_path)
            raise LocalDatabaseIntegrityError("LOCAL_DATABASE_ERROR") from error
        except BaseException:
            self._connection.close()
            self._closed = True
            raise

    def __enter__(self) -> "Repository":
        self._ensure_open()
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.close()

    def _ensure_open(self) -> None:
        if self._closed:
            raise RepositoryError("Repository is closed")

    def close(self) -> None:
        """Close the owned connection; repeated calls are harmless."""
        if not self._closed:
            self._connection.close()
            self._closed = True

    @property
    def schema_version(self) -> int:
        """Return the currently applied migration version."""
        self._ensure_open()
        return get_schema_version(self._connection)

    def get_schema_meta(self) -> dict[str, str]:
        """Return schema metadata as an ordinary mapping."""
        self._ensure_open()
        rows = self._connection.execute("SELECT key, value FROM schema_meta").fetchall()
        return {row["key"]: row["value"] for row in rows}

    def set_schema_meta(self, key: str, value: str) -> None:
        """Set non-version schema metadata such as the device ID."""
        self._ensure_open()
        if key == "schema_version":
            raise ValueError("schema_version is owned by the migration runner")
        with transaction(self._connection) as connection:
            connection.execute(
                "INSERT INTO schema_meta(key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def get_or_create_device_id(self) -> str:
        """Return the stable UUIDv4 identity, creating it atomically once."""
        self._ensure_open()
        with transaction(self._connection) as connection:
            row = connection.execute(
                "SELECT value FROM schema_meta WHERE key = 'device_id'"
            ).fetchone()
            if row is not None and row["value"]:
                return str(uuid.UUID(row["value"]))
            device_id = str(uuid.uuid4())
            connection.execute(
                "INSERT INTO schema_meta(key, value) VALUES ('device_id', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (device_id,),
            )
            return device_id

    def create_profile(
        self,
        profile: Profile,
        *,
        pin_hash: str | None = None,
        pin_salt: str | None = None,
        created_at: datetime | None = None,
    ) -> Profile:
        """Persist profile data without implementing PIN behavior."""
        self._ensure_open()
        created_text = datetime_to_text(created_at) if created_at else utc_now_text()
        with transaction(self._connection) as connection:
            connection.execute(
                "INSERT INTO profiles("
                "id, display_name, server_user_id, pin_hash, pin_salt, created_at"
                ") VALUES (?, ?, ?, ?, ?, ?)",
                (
                    profile.id,
                    profile.display_name,
                    profile.server_user_id,
                    pin_hash,
                    pin_salt,
                    created_text,
                ),
            )
        return profile

    def get_profile(self, profile_id: str) -> Profile | None:
        """Return one profile, including a soft-deleted profile when requested by ID."""
        self._ensure_open()
        row = self._connection.execute(
            "SELECT id, display_name, server_user_id FROM profiles WHERE id = ?",
            (profile_id,),
        ).fetchone()
        return self._profile_from_row(row) if row else None

    def list_profiles(self) -> tuple[Profile, ...]:
        """Return active profiles in stable creation/ID order."""
        self._ensure_open()
        rows = self._connection.execute(
            "SELECT id, display_name, server_user_id FROM profiles "
            "WHERE deleted_at IS NULL ORDER BY created_at, id"
        ).fetchall()
        return tuple(self._profile_from_row(row) for row in rows)

    def soft_delete_profile(
        self, profile_id: str, *, deleted_at: datetime | None = None
    ) -> bool:
        """Soft-delete a profile and report whether a live row changed."""
        deleted_text = datetime_to_text(deleted_at) if deleted_at else utc_now_text()
        with transaction(self._connection) as connection:
            cursor = connection.execute(
                "UPDATE profiles SET deleted_at = ? "
                "WHERE id = ? AND deleted_at IS NULL",
                (deleted_text, profile_id),
            )
        return cursor.rowcount == 1

    @staticmethod
    def _profile_from_row(row: sqlite3.Row) -> Profile:
        return Profile(
            id=row["id"],
            display_name=row["display_name"],
            server_user_id=row["server_user_id"],
        )

    def insert_question_set(
        self,
        question_set: QuestionSet,
        *,
        content_hash: str,
        downloaded_at: datetime | None = None,
        is_active: bool = False,
    ) -> None:
        """Insert immutable set metadata; questions are inserted separately."""
        downloaded_text = datetime_to_text(downloaded_at) if downloaded_at else utc_now_text()
        try:
            with transaction(self._connection) as connection:
                self._insert_question_set_row(
                    connection,
                    question_set,
                    content_hash,
                    downloaded_text,
                    is_active,
                )
        except sqlite3.IntegrityError as error:
            if self._question_set_exists(question_set.id, question_set.version):
                raise DuplicateQuestionSetVersion(
                    f"Question set {question_set.id!r} version {question_set.version} already exists"
                ) from error
            raise

    def import_question_set(
        self,
        question_set: QuestionSet,
        *,
        content_hash: str,
        downloaded_at: datetime | None = None,
        is_active: bool = False,
    ) -> None:
        """Atomically insert immutable set metadata, questions, and activation."""
        downloaded_text = datetime_to_text(downloaded_at) if downloaded_at else utc_now_text()
        try:
            with transaction(self._connection) as connection:
                self._insert_question_set_row(
                    connection,
                    question_set,
                    content_hash,
                    downloaded_text,
                    False,
                )
                self._insert_question_rows(
                    connection, question_set.id, question_set.version, question_set.questions
                )
                self._fault_hook("BEFORE_PACK_IMPORT_COMMIT")
                if is_active:
                    connection.execute(
                        "UPDATE question_sets SET is_active = 0 WHERE id = ?",
                        (question_set.id,),
                    )
                    connection.execute(
                        "UPDATE question_sets SET is_active = 1 "
                        "WHERE id = ? AND version = ?",
                        (question_set.id, question_set.version),
                    )
            self._fault_hook("AFTER_PACK_IMPORT_COMMIT")
        except sqlite3.IntegrityError as error:
            if self._question_set_exists(question_set.id, question_set.version):
                raise DuplicateQuestionSetVersion(
                    f"Question set {question_set.id!r} version {question_set.version} already exists"
                ) from error
            raise

    @staticmethod
    def _insert_question_set_row(
        connection: sqlite3.Connection,
        question_set: QuestionSet,
        content_hash: str,
        downloaded_at: str,
        is_active: bool,
    ) -> None:
        marking_json = json.dumps(
            {
                "correct": question_set.marking.correct,
                "wrong": question_set.marking.wrong,
                "skip": question_set.marking.skip,
            },
            separators=(",", ":"),
            sort_keys=True,
        )
        connection.execute(
            "INSERT INTO question_sets("
            "id, version, title, subject, chapter, marking_json, content_hash, "
            "downloaded_at, is_active"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                question_set.id,
                question_set.version,
                question_set.title,
                question_set.subject,
                question_set.chapter,
                marking_json,
                content_hash,
                downloaded_at,
                int(is_active),
            ),
        )

    def _question_set_exists(self, set_id: str, version: int) -> bool:
        row = self._connection.execute(
            "SELECT 1 FROM question_sets WHERE id = ? AND version = ?",
            (set_id, version),
        ).fetchone()
        return row is not None

    def insert_questions(
        self, set_id: str, version: int, questions: Sequence[Question]
    ) -> None:
        """Bulk-insert questions for one exact set version atomically."""
        with transaction(self._connection) as connection:
            self._insert_question_rows(connection, set_id, version, questions)

    @staticmethod
    def _insert_question_rows(
        connection: sqlite3.Connection,
        set_id: str,
        version: int,
        questions: Sequence[Question],
    ) -> None:
        rows = []
        for question in questions:
            options_json = json.dumps(
                [{"key": option.key, "text": option.text} for option in question.options],
                ensure_ascii=False,
                separators=(",", ":"),
            )
            rows.append(
                (
                    set_id,
                    version,
                    question.id,
                    question.position,
                    question.topic,
                    question.difficulty,
                    question.question_text,
                    options_json,
                    question.correct_key,
                    question.explanation,
                    question.media_ref,
                )
            )
        connection.executemany(
            "INSERT INTO questions("
            "set_id, set_version, id, position, topic, difficulty, question_text, "
            "options_json, correct_key, explanation, media_ref"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )

    def get_questions(self, set_id: str, version: int) -> tuple[Question, ...]:
        """Return exact-version questions ordered only by persisted position."""
        rows = self._connection.execute(
            "SELECT * FROM questions WHERE set_id = ? AND set_version = ? "
            "ORDER BY position",
            (set_id, version),
        ).fetchall()
        return tuple(self._question_from_row(row) for row in rows)

    def get_question(self, set_id: str, version: int, question_id: str) -> Question | None:
        """Return one question in an exact set version."""
        row = self._connection.execute(
            "SELECT * FROM questions WHERE set_id = ? AND set_version = ? AND id = ?",
            (set_id, version, question_id),
        ).fetchone()
        return self._question_from_row(row) if row else None

    @staticmethod
    def _question_from_row(row: sqlite3.Row) -> Question:
        options_data = json.loads(row["options_json"])
        options = tuple(Option(key=item["key"], text=item["text"]) for item in options_data)
        return Question(
            id=row["id"],
            position=row["position"],
            topic=row["topic"],
            difficulty=row["difficulty"],
            question_text=row["question_text"],
            options=options,
            correct_key=row["correct_key"],
            explanation=row["explanation"],
            media_ref=row["media_ref"],
        )

    def get_question_set(self, set_id: str, version: int) -> QuestionSet | None:
        """Load an exact immutable set version as a complete domain aggregate."""
        row = self._connection.execute(
            "SELECT * FROM question_sets WHERE id = ? AND version = ?",
            (set_id, version),
        ).fetchone()
        if row is None:
            return None
        questions = self.get_questions(set_id, version)
        if not questions:
            raise DataIntegrityError(
                f"Question set {set_id!r} version {version} contains no questions"
            )
        marking_data = json.loads(row["marking_json"])
        return QuestionSet(
            id=row["id"],
            version=row["version"],
            title=row["title"],
            subject=row["subject"],
            chapter=row["chapter"],
            marking=MarkingScheme(**marking_data),
            questions=questions,
        )

    def get_question_set_persistence(
        self, set_id: str, version: int
    ) -> QuestionSetPersistence | None:
        """Return exact-byte hash, installation time, and activation state."""
        row = self._connection.execute(
            "SELECT content_hash, downloaded_at, is_active FROM question_sets "
            "WHERE id = ? AND version = ?",
            (set_id, version),
        ).fetchone()
        if row is None:
            return None
        downloaded_at = datetime_from_text(row["downloaded_at"])
        if downloaded_at is None:
            raise DataIntegrityError("Question-set downloaded_at is missing")
        return QuestionSetPersistence(
            content_hash=row["content_hash"],
            downloaded_at=downloaded_at,
            is_active=bool(row["is_active"]),
        )

    def list_question_sets(self, set_id: str | None = None) -> tuple[QuestionSet, ...]:
        """Return complete set versions ordered by logical ID and version."""
        if set_id is None:
            rows = self._connection.execute(
                "SELECT id, version FROM question_sets ORDER BY id, version"
            ).fetchall()
        else:
            rows = self._connection.execute(
                "SELECT id, version FROM question_sets WHERE id = ? ORDER BY version",
                (set_id,),
            ).fetchall()
        result = []
        for row in rows:
            question_set = self.get_question_set(row["id"], row["version"])
            if question_set is not None:
                result.append(question_set)
        return tuple(result)

    def list_question_set_versions(self, set_id: str) -> tuple[int, ...]:
        """Return installed versions for one logical set ID."""
        rows = self._connection.execute(
            "SELECT version FROM question_sets WHERE id = ? ORDER BY version", (set_id,)
        ).fetchall()
        return tuple(row["version"] for row in rows)

    def set_active_question_set(self, set_id: str, version: int) -> None:
        """Atomically make one installed version active for a logical set."""
        with transaction(self._connection) as connection:
            target = connection.execute(
                "SELECT 1 FROM question_sets WHERE id = ? AND version = ?",
                (set_id, version),
            ).fetchone()
            if target is None:
                raise UnknownQuestionSet(f"Unknown question set {set_id!r} version {version}")
            connection.execute("UPDATE question_sets SET is_active = 0 WHERE id = ?", (set_id,))
            connection.execute(
                "UPDATE question_sets SET is_active = 1 WHERE id = ? AND version = ?",
                (set_id, version),
            )

    def get_active_question_set(self, set_id: str) -> QuestionSet | None:
        """Return the active installed version of one logical set."""
        row = self._connection.execute(
            "SELECT version FROM question_sets WHERE id = ? AND is_active = 1",
            (set_id,),
        ).fetchone()
        return self.get_question_set(set_id, row["version"]) if row else None

    def create_attempt(
        self,
        attempt: Attempt,
        *,
        question_order: Sequence[str] | None = None,
        sync_status: SyncStatus = SyncStatus.LOCAL,
    ) -> Attempt:
        """Persist an attempt and optional fixed question order atomically."""
        with transaction(self._connection) as connection:
            self._insert_attempt(connection, attempt, sync_status)
            if question_order is not None:
                self._insert_attempt_order(connection, attempt.id, question_order)
        return attempt

    @staticmethod
    def _insert_attempt(
        connection: sqlite3.Connection, attempt: Attempt, sync_status: SyncStatus
    ) -> None:
        started_at = datetime_to_text(attempt.started_at) if attempt.started_at else utc_now_text()
        completed_at = (
            datetime_to_text(attempt.completed_at) if attempt.completed_at is not None else None
        )
        connection.execute(
            "INSERT INTO attempts("
            "id, profile_id, set_id, set_version, status, started_at, completed_at, "
            "duration_ms, score, sync_status"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                attempt.id,
                attempt.profile_id,
                attempt.set_id,
                attempt.set_version,
                attempt.status,
                started_at,
                completed_at,
                attempt.duration_ms,
                attempt.score,
                sync_status,
            ),
        )

    def get_attempt(self, attempt_id: str) -> Attempt | None:
        """Return one attempt as a core domain model."""
        row = self._connection.execute(
            "SELECT * FROM attempts WHERE id = ?", (attempt_id,)
        ).fetchone()
        return self._attempt_from_row(row) if row else None

    @staticmethod
    def _attempt_from_row(row: sqlite3.Row) -> Attempt:
        return Attempt(
            id=row["id"],
            profile_id=row["profile_id"],
            set_id=row["set_id"],
            set_version=row["set_version"],
            status=AttemptStatus(row["status"]),
            started_at=datetime_from_text(row["started_at"]),
            completed_at=datetime_from_text(row["completed_at"]),
            duration_ms=row["duration_ms"],
            score=row["score"],
        )

    def get_attempt_sync_state(self, attempt_id: str) -> AttemptSyncState:
        """Return persistence-only sync metadata for an attempt."""
        row = self._connection.execute(
            "SELECT sync_status, sync_attempts, last_sync_error, synced_at, "
            "next_sync_at, sync_started_at, sync_error_kind "
            "FROM attempts WHERE id = ?",
            (attempt_id,),
        ).fetchone()
        if row is None:
            raise UnknownAttempt(f"Unknown attempt {attempt_id!r}")
        return AttemptSyncState(
            status=SyncStatus(row["sync_status"]),
            attempts=row["sync_attempts"],
            last_error=row["last_sync_error"],
            synced_at=datetime_from_text(row["synced_at"]),
            next_sync_at=datetime_from_text(row["next_sync_at"]),
            sync_started_at=datetime_from_text(row["sync_started_at"]),
            error_kind=row["sync_error_kind"],
        )

    def find_in_progress_attempt(self, profile_id: str) -> Attempt | None:
        """Return the profile's sole in-progress attempt, newest first defensively."""
        rows = self._connection.execute(
            "SELECT * FROM attempts WHERE profile_id = ? AND status = 'in_progress' "
            "ORDER BY started_at DESC, id DESC LIMIT 2",
            (profile_id,),
        ).fetchall()
        if len(rows) > 1:
            raise DataIntegrityError(f"Profile {profile_id!r} has multiple in-progress attempts")
        return self._attempt_from_row(rows[0]) if rows else None

    def complete_attempt(
        self,
        attempt_id: str,
        *,
        completed_at: datetime,
        duration_ms: int,
        score: int | float,
    ) -> Attempt:
        """Atomically complete an attempt and mark it pending upload."""
        completed_text = datetime_to_text(completed_at)
        with transaction(self._connection) as connection:
            cursor = connection.execute(
                "UPDATE attempts SET status = 'completed', completed_at = ?, "
                "duration_ms = ?, score = ?, sync_status = 'pending', "
                "sync_attempts = 0, last_sync_error = NULL, synced_at = NULL, "
                "next_sync_at = NULL, sync_started_at = NULL, sync_error_kind = NULL "
                "WHERE id = ? AND status = 'in_progress'",
                (completed_text, duration_ms, score, attempt_id),
            )
            if cursor.rowcount != 1:
                self._raise_unknown_or_invalid_attempt(connection, attempt_id, "complete")
            self._fault_hook("BEFORE_ATTEMPT_COMPLETION_COMMIT")
        self._fault_hook("AFTER_ATTEMPT_COMPLETION_COMMIT")
        completed = self.get_attempt(attempt_id)
        if completed is None:
            raise UnknownAttempt(f"Unknown attempt {attempt_id!r}")
        return completed

    def mark_attempt_abandoned(
        self, attempt_id: str, *, completed_at: datetime | None = None
    ) -> Attempt:
        """Atomically mark an in-progress attempt abandoned."""
        completed_text = datetime_to_text(completed_at) if completed_at else utc_now_text()
        with transaction(self._connection) as connection:
            cursor = connection.execute(
                "UPDATE attempts SET status = 'abandoned', completed_at = ? "
                "WHERE id = ? AND status = 'in_progress'",
                (completed_text, attempt_id),
            )
            if cursor.rowcount != 1:
                self._raise_unknown_or_invalid_attempt(connection, attempt_id, "abandon")
        abandoned = self.get_attempt(attempt_id)
        if abandoned is None:
            raise UnknownAttempt(f"Unknown attempt {attempt_id!r}")
        return abandoned

    @staticmethod
    def _raise_unknown_or_invalid_attempt(
        connection: sqlite3.Connection, attempt_id: str, operation: str
    ) -> None:
        row = connection.execute("SELECT status FROM attempts WHERE id = ?", (attempt_id,)).fetchone()
        if row is None:
            raise UnknownAttempt(f"Unknown attempt {attempt_id!r}")
        raise RepositoryError(
            f"Cannot {operation} attempt {attempt_id!r} from status {row['status']!r}"
        )

    def get_pending_attempts(self, *, limit: int | None = None) -> tuple[Attempt, ...]:
        """Return completed attempts awaiting or needing another future upload."""
        sql = (
            "SELECT * FROM attempts WHERE status = 'completed' "
            "AND sync_status IN ('pending', 'failed') "
            "ORDER BY completed_at, id"
        )
        parameters: tuple[int, ...] = ()
        if limit is not None:
            if limit < 1:
                raise ValueError("Pending-attempt limit must be positive")
            sql += " LIMIT ?"
            parameters = (limit,)
        rows = self._connection.execute(sql, parameters).fetchall()
        return tuple(self._attempt_from_row(row) for row in rows)

    def get_sync_eligible_attempts(
        self,
        *,
        now: datetime,
        limit: int,
        max_attempts: int,
    ) -> tuple[Attempt, ...]:
        """Return due completed attempts in stable oldest-first order."""
        if limit < 1:
            raise ValueError("Sync batch limit must be positive")
        if max_attempts < 1:
            raise ValueError("Maximum sync attempts must be positive")
        now_text = datetime_to_text(now)
        rows = self._connection.execute(
            "SELECT * FROM attempts WHERE status = 'completed' AND ("
            "sync_status = 'pending' OR ("
            "sync_status = 'failed' AND sync_attempts < ? "
            "AND (sync_error_kind IS NULL OR sync_error_kind = 'transient') "
            "AND (next_sync_at IS NULL OR next_sync_at <= ?)"
            ")) ORDER BY completed_at, id LIMIT ?",
            (max_attempts, now_text, limit),
        ).fetchall()
        return tuple(self._attempt_from_row(row) for row in rows)

    def mark_attempt_syncing(self, attempt_id: str, *, started_at: datetime) -> None:
        """Persist ownership of one eligible upload before network I/O."""
        with transaction(self._connection) as connection:
            cursor = connection.execute(
                "UPDATE attempts SET sync_status = 'syncing', sync_started_at = ?, "
                "next_sync_at = NULL WHERE id = ? AND status = 'completed' "
                "AND sync_status IN ('pending', 'failed')",
                (datetime_to_text(started_at), attempt_id),
            )
            if cursor.rowcount != 1:
                self._raise_unknown_or_invalid_attempt(connection, attempt_id, "start sync for")

    def mark_attempt_synced(self, attempt_id: str, *, synced_at: datetime) -> None:
        """Persist a successful or proven-idempotent server acknowledgement."""
        with transaction(self._connection) as connection:
            cursor = connection.execute(
                "UPDATE attempts SET sync_status = 'synced', synced_at = ?, "
                "last_sync_error = NULL, next_sync_at = NULL, sync_started_at = NULL, "
                "sync_error_kind = NULL WHERE id = ? AND status = 'completed' "
                "AND sync_status = 'syncing'",
                (datetime_to_text(synced_at), attempt_id),
            )
            if cursor.rowcount != 1:
                self._raise_unknown_or_invalid_attempt(connection, attempt_id, "finish sync for")

    def mark_attempt_sync_failed(
        self,
        attempt_id: str,
        *,
        error: str,
        error_kind: str,
        next_sync_at: datetime | None,
    ) -> None:
        """Record one failed upload without deleting or changing assessment data."""
        if error_kind not in {"transient", "permanent", "authentication"}:
            raise ValueError("Unknown sync error kind")
        with transaction(self._connection) as connection:
            cursor = connection.execute(
                "UPDATE attempts SET sync_status = 'failed', "
                "sync_attempts = sync_attempts + 1, last_sync_error = ?, "
                "next_sync_at = ?, sync_started_at = NULL, sync_error_kind = ? "
                "WHERE id = ? AND status = 'completed' AND sync_status = 'syncing'",
                (
                    error[:500],
                    datetime_to_text(next_sync_at) if next_sync_at else None,
                    error_kind,
                    attempt_id,
                ),
            )
            if cursor.rowcount != 1:
                self._raise_unknown_or_invalid_attempt(connection, attempt_id, "fail sync for")

    def recover_stale_syncing(self, *, now: datetime, stale_after: timedelta) -> int:
        """Return old in-flight rows to pending so a later idempotent upload can retry."""
        if stale_after.total_seconds() < 0:
            raise ValueError("Stale threshold must not be negative")
        cutoff = now - stale_after
        with transaction(self._connection) as connection:
            cursor = connection.execute(
                "UPDATE attempts SET sync_status = 'pending', sync_started_at = NULL, "
                "next_sync_at = NULL, sync_error_kind = 'transient', "
                "last_sync_error = 'stale syncing state recovered' "
                "WHERE status = 'completed' AND sync_status = 'syncing' "
                "AND (sync_started_at IS NULL OR sync_started_at <= ?)",
                (datetime_to_text(cutoff),),
            )
        return cursor.rowcount

    def requeue_failed_attempt(self, attempt_id: str, *, reset_attempts: bool = True) -> None:
        """Explicitly make a retained failed attempt eligible for a manual retry."""
        with transaction(self._connection) as connection:
            if reset_attempts:
                cursor = connection.execute(
                    "UPDATE attempts SET sync_status = 'pending', sync_attempts = 0, "
                    "last_sync_error = NULL, next_sync_at = NULL, sync_started_at = NULL, "
                    "sync_error_kind = NULL WHERE id = ? AND status = 'completed' "
                    "AND sync_status = 'failed'",
                    (attempt_id,),
                )
            else:
                cursor = connection.execute(
                    "UPDATE attempts SET sync_status = 'pending', last_sync_error = NULL, "
                    "next_sync_at = NULL, sync_started_at = NULL, sync_error_kind = NULL "
                    "WHERE id = ? AND status = 'completed' AND sync_status = 'failed'",
                    (attempt_id,),
                )
            if cursor.rowcount != 1:
                self._raise_unknown_or_invalid_attempt(connection, attempt_id, "requeue sync for")

    def save_attempt_question_order(
        self, attempt_id: str, question_ids: Sequence[str]
    ) -> None:
        """Save a complete fixed order exactly once in one transaction."""
        with transaction(self._connection) as connection:
            self._insert_attempt_order(connection, attempt_id, question_ids)

    def _insert_attempt_order(
        self, connection: sqlite3.Connection, attempt_id: str, question_ids: Sequence[str]
    ) -> None:
        attempt = connection.execute(
            "SELECT set_id, set_version FROM attempts WHERE id = ?", (attempt_id,)
        ).fetchone()
        if attempt is None:
            raise UnknownAttempt(f"Unknown attempt {attempt_id!r}")
        existing = connection.execute(
            "SELECT 1 FROM attempt_questions WHERE attempt_id = ? LIMIT 1", (attempt_id,)
        ).fetchone()
        if existing is not None:
            raise AttemptQuestionOrderAlreadyExists(
                f"Question order already exists for attempt {attempt_id!r}"
            )
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("Attempt question order contains duplicate question IDs")
        available_rows = connection.execute(
            "SELECT id FROM questions WHERE set_id = ? AND set_version = ?",
            (attempt["set_id"], attempt["set_version"]),
        ).fetchall()
        available_ids = {row["id"] for row in available_rows}
        unknown_ids = [question_id for question_id in question_ids if question_id not in available_ids]
        if unknown_ids:
            raise ValueError(f"Attempt order contains unknown question IDs: {unknown_ids!r}")
        connection.executemany(
            "INSERT INTO attempt_questions(attempt_id, position, question_id) VALUES (?, ?, ?)",
            [
                (attempt_id, position, question_id)
                for position, question_id in enumerate(question_ids, start=1)
            ],
        )

    def get_attempt_question_order(self, attempt_id: str) -> tuple[str, ...]:
        """Return exactly the persisted attempt order by stored position."""
        rows = self._connection.execute(
            "SELECT question_id FROM attempt_questions WHERE attempt_id = ? ORDER BY position",
            (attempt_id,),
        ).fetchall()
        return tuple(row["question_id"] for row in rows)

    def save_response(
        self,
        response: Response,
        *,
        is_correct: bool | None,
        first_shown_at: datetime | None = None,
        answered_at: datetime | None = None,
    ) -> Response:
        """Insert or update current response state while preserving its first ID."""
        first_shown_text = (
            datetime_to_text(first_shown_at) if first_shown_at is not None else None
        )
        answered_text = datetime_to_text(answered_at) if answered_at is not None else None
        with transaction(self._connection) as connection:
            connection.execute(
                "INSERT INTO responses("
                "id, attempt_id, question_id, selected_key, confidence, is_correct, "
                "response_time_ms, first_shown_at, answered_at, marked_review"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(attempt_id, question_id) DO UPDATE SET "
                "selected_key = excluded.selected_key, confidence = excluded.confidence, "
                "is_correct = excluded.is_correct, response_time_ms = excluded.response_time_ms, "
                "first_shown_at = COALESCE(responses.first_shown_at, excluded.first_shown_at), "
                "answered_at = COALESCE(excluded.answered_at, responses.answered_at), "
                "marked_review = excluded.marked_review",
                (
                    response.id,
                    response.attempt_id,
                    response.question_id,
                    response.selected_key,
                    response.confidence,
                    None if is_correct is None else int(is_correct),
                    response.response_time_ms,
                    first_shown_text,
                    answered_text,
                    int(response.marked_review),
                ),
            )
            self._fault_hook("BEFORE_RESPONSE_COMMIT")
        self._fault_hook("AFTER_RESPONSE_COMMIT")
        stored = self.get_response(response.attempt_id, response.question_id)
        if stored is None:
            raise DataIntegrityError("Saved response could not be reloaded")
        return stored

    def get_response(self, attempt_id: str, question_id: str) -> Response | None:
        """Return current domain response state for one attempt question."""
        row = self._connection.execute(
            "SELECT * FROM responses WHERE attempt_id = ? AND question_id = ?",
            (attempt_id, question_id),
        ).fetchone()
        return self._response_from_row(row) if row else None

    def get_attempt_responses(self, attempt_id: str) -> tuple[Response, ...]:
        """Return current responses in the persisted attempt question order."""
        rows = self._connection.execute(
            "SELECT responses.* FROM responses "
            "JOIN attempt_questions ON attempt_questions.attempt_id = responses.attempt_id "
            "AND attempt_questions.question_id = responses.question_id "
            "WHERE responses.attempt_id = ? ORDER BY attempt_questions.position",
            (attempt_id,),
        ).fetchall()
        return tuple(self._response_from_row(row) for row in rows)

    @staticmethod
    def _response_from_row(row: sqlite3.Row) -> Response:
        confidence = Confidence(row["confidence"]) if row["confidence"] is not None else None
        return Response(
            id=row["id"],
            attempt_id=row["attempt_id"],
            question_id=row["question_id"],
            selected_key=row["selected_key"],
            confidence=confidence,
            response_time_ms=row["response_time_ms"],
            marked_review=bool(row["marked_review"]),
        )

    def get_response_persistence(
        self, attempt_id: str, question_id: str
    ) -> ResponsePersistence | None:
        """Return data-only correctness and audit timestamp fields."""
        row = self._connection.execute(
            "SELECT is_correct, first_shown_at, answered_at FROM responses "
            "WHERE attempt_id = ? AND question_id = ?",
            (attempt_id, question_id),
        ).fetchone()
        if row is None:
            return None
        return ResponsePersistence(
            is_correct=None if row["is_correct"] is None else bool(row["is_correct"]),
            first_shown_at=datetime_from_text(row["first_shown_at"]),
            answered_at=datetime_from_text(row["answered_at"]),
        )

    def set_confidence(
        self, attempt_id: str, question_id: str, confidence: Confidence
    ) -> Response:
        """Update confidence for an existing answered response."""
        with transaction(self._connection) as connection:
            cursor = connection.execute(
                "UPDATE responses SET confidence = ? "
                "WHERE attempt_id = ? AND question_id = ? AND selected_key IS NOT NULL",
                (confidence, attempt_id, question_id),
            )
            if cursor.rowcount != 1:
                raise RepositoryError(
                    f"No answered response for attempt {attempt_id!r}, question {question_id!r}"
                )
        response = self.get_response(attempt_id, question_id)
        if response is None:
            raise DataIntegrityError("Updated response could not be reloaded")
        return response

    def set_marked_review(
        self, attempt_id: str, question_id: str, marked_review: bool
    ) -> Response:
        """Set or clear the current response review marker."""
        with transaction(self._connection) as connection:
            cursor = connection.execute(
                "UPDATE responses SET marked_review = ? "
                "WHERE attempt_id = ? AND question_id = ?",
                (int(marked_review), attempt_id, question_id),
            )
            if cursor.rowcount != 1:
                raise RepositoryError(
                    f"No response for attempt {attempt_id!r}, question {question_id!r}"
                )
        response = self.get_response(attempt_id, question_id)
        if response is None:
            raise DataIntegrityError("Updated response could not be reloaded")
        return response

    def append_response_event(
        self,
        *,
        event_id: str,
        attempt_id: str,
        question_id: str,
        event_type: str,
        value: str | None,
        at_ms: int,
        at_utc: datetime,
    ) -> ResponseEvent:
        """Append one history event without changing current response state."""
        at_utc_text = datetime_to_text(at_utc)
        with transaction(self._connection) as connection:
            connection.execute(
                "INSERT INTO response_events("
                "id, attempt_id, question_id, event_type, value, at_ms, at_utc"
                ") VALUES (?, ?, ?, ?, ?, ?, ?)",
                (event_id, attempt_id, question_id, event_type, value, at_ms, at_utc_text),
            )
        return ResponseEvent(
            id=event_id,
            attempt_id=attempt_id,
            question_id=question_id,
            event_type=event_type,
            value=value,
            at_ms=at_ms,
            at_utc=at_utc,
        )

    def get_response_events(self, attempt_id: str) -> tuple[ResponseEvent, ...]:
        """Return append-only events in stable elapsed-time/ID order."""
        rows = self._connection.execute(
            "SELECT * FROM response_events WHERE attempt_id = ? ORDER BY at_ms, id",
            (attempt_id,),
        ).fetchall()
        return tuple(
            ResponseEvent(
                id=row["id"],
                attempt_id=row["attempt_id"],
                question_id=row["question_id"],
                event_type=row["event_type"],
                value=row["value"],
                at_ms=row["at_ms"],
                at_utc=datetime_from_text(row["at_utc"]),
            )
            for row in rows
        )

    def set_setting(self, key: str, value: str) -> None:
        """Insert or replace a non-secret application setting."""
        with transaction(self._connection) as connection:
            connection.execute(
                "INSERT INTO settings(key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def get_setting(self, key: str) -> str | None:
        """Return a setting value, or None when absent."""
        row = self._connection.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else None

    def delete_setting(self, key: str) -> bool:
        """Delete a setting and report whether it existed."""
        with transaction(self._connection) as connection:
            cursor = connection.execute("DELETE FROM settings WHERE key = ?", (key,))
        return cursor.rowcount == 1

    def integrity_check(self) -> IntegrityCheckResult:
        """Run SQLite's integrity checker on this repository database."""
        return check_integrity(self._connection)

    def quick_check(self) -> IntegrityCheckResult:
        """Run the lightweight read-only SQLite health check."""
        return quick_check(self._connection)

    def diagnostic_attempt_summary(self, *, limit: int = 10) -> tuple[dict[str, object], ...]:
        """Return minimized attempt metadata without profiles, answers, or confidence."""
        rows = self._connection.execute(
            "SELECT id, status, set_id, set_version, sync_status, started_at, completed_at "
            "FROM attempts ORDER BY started_at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return tuple(dict(row) for row in rows)

    def sync_diagnostic_summary(self) -> dict[str, object]:
        """Return aggregate queue and last-event information without assessment content."""
        counts = {
            status.value: self.count_attempts_by_sync_status(status) for status in SyncStatus
        }
        last_success = self._connection.execute(
            "SELECT MAX(synced_at) AS value FROM attempts WHERE synced_at IS NOT NULL"
        ).fetchone()["value"]
        failure = self._connection.execute(
            "SELECT last_sync_error, sync_error_kind, completed_at FROM attempts "
            "WHERE sync_status = 'failed' ORDER BY completed_at DESC, id DESC LIMIT 1"
        ).fetchone()
        in_progress = self._connection.execute(
            "SELECT COUNT(*) AS count FROM attempts WHERE status = 'in_progress'"
        ).fetchone()["count"]
        auth_required = self._connection.execute(
            "SELECT COUNT(*) AS count FROM attempts WHERE sync_status = 'failed' "
            "AND sync_error_kind = 'authentication'"
        ).fetchone()["count"]
        return {
            "counts": counts,
            "in_progress": int(in_progress),
            "auth_required": int(auth_required),
            "last_success": last_success,
            "last_failure": failure["completed_at"] if failure else None,
            "last_error_kind": failure["sync_error_kind"] if failure else None,
            "last_error": failure["last_sync_error"] if failure else None,
        }

    def count_attempts_by_sync_status(self, status: SyncStatus) -> int:
        """Return a non-sensitive aggregate for diagnostics."""
        row = self._connection.execute(
            "SELECT COUNT(*) AS count FROM attempts WHERE sync_status = ?", (status.value,)
        ).fetchone()
        return int(row["count"])

    def backup_to(self, destination: Path) -> None:
        """Create a one-shot online backup at the supplied path."""
        try:
            backup_database(self._connection, destination)
        except (OSError, sqlite3.Error):
            LOGGER.exception("local database backup failed destination=%s", destination)
            raise

