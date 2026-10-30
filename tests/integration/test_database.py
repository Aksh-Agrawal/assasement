"""Integration tests for SQLite configuration, migrations, and maintenance."""

import shutil
import sqlite3
from pathlib import Path

import pytest

from app.data.db import (
    MIGRATIONS_DIRECTORY,
    backup_database,
    check_integrity,
    connect_database,
    get_schema_version,
    run_migrations,
)
from app.data.repo import Repository, RepositoryError

EXPECTED_TABLES = {
    "institute_work", "attempt_institute_context",
    "private_pack_versions",
    "profile_library",
    "student_account_context",
    "profile_link_context",
    "attempt_ownership",
    "attempt_questions",
    "attempts",
    "profiles",
    "question_sets",
    "questions",
    "response_events",
    "responses",
    "schema_meta",
    "settings",
}


def test_failed_connection_setup_closes_handle_and_preserves_corrupt_file(tmp_path, monkeypatch):
    path = tmp_path / "corrupt.db"
    original = b"Not a SQLite database"
    path.write_bytes(original)
    opened = []
    real_connect = sqlite3.connect

    def record_connection(*args, **kwargs):
        connection = real_connect(*args, **kwargs)
        opened.append(connection)
        return connection

    monkeypatch.setattr("app.data.db.sqlite3.connect", record_connection)
    with pytest.raises(sqlite3.DatabaseError):
        connect_database(path)
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        opened[0].execute("SELECT 1")
    assert path.read_bytes() == original
    retained = tmp_path / "retained-corrupt.db"
    path.rename(retained)
    assert retained.read_bytes() == original


def test_fresh_database_migrates_and_second_run_is_idempotent(tmp_path: Path) -> None:
    database_path = tmp_path / "fresh.db"
    connection = connect_database(database_path)
    try:
        first_version = run_migrations(connection)
        first_tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        second_version = run_migrations(connection)
        second_tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
    finally:
        connection.close()

    reopened = connect_database(database_path)
    try:
        recorded_version = get_schema_version(reopened)
    finally:
        reopened.close()

    assert first_version == 7
    assert second_version == 7
    assert recorded_version == 7
    assert first_tables == EXPECTED_TABLES
    assert second_tables == first_tables


def test_file_database_uses_required_pragmas(tmp_path: Path) -> None:
    connection = connect_database(tmp_path / "pragmas.db")
    try:
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert connection.execute("PRAGMA synchronous").fetchone()[0] == 2
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert connection.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
        assert connection.execute("PRAGMA wal_autocheckpoint").fetchone()[0] == 1000
    finally:
        connection.close()


def test_foreign_keys_reject_invalid_writes(tmp_path: Path) -> None:
    connection = connect_database(tmp_path / "foreign-keys.db")
    try:
        run_migrations(connection)
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO attempts("
                "id, profile_id, set_id, set_version, status, started_at"
                ") VALUES ('attempt', 'missing-profile', 'missing-set', 1, "
                "'in_progress', '2026-01-01T00:00:00.000Z')"
            )
    finally:
        connection.close()


def test_integrity_check_and_online_backup(tmp_path: Path) -> None:
    source_path = tmp_path / "source.db"
    backup_path = tmp_path / "backup.db"
    connection = connect_database(source_path)
    try:
        run_migrations(connection)
        result = check_integrity(connection)
        backup_database(connection, backup_path)
    finally:
        connection.close()

    backup_connection = connect_database(backup_path)
    try:
        assert result.ok is True
        assert result.messages == ("ok",)
        assert get_schema_version(backup_connection) == 7
        assert check_integrity(backup_connection).ok is True
    finally:
        backup_connection.close()


def test_repository_context_manager_closes_connection(tmp_path: Path) -> None:
    database_path = tmp_path / "lifecycle.db"
    repository = Repository(database_path)

    with repository:
        assert repository.schema_version == 7

    with pytest.raises(RepositoryError, match="closed"):
        _ = repository.schema_version
    database_path.unlink()
    assert not database_path.exists()


def test_phase_8_schema_migrates_without_losing_assessment_data(tmp_path: Path) -> None:
    """A real version-1 database retains all assessment tables through migration 0002."""
    prior_migrations = tmp_path / "prior-migrations"
    prior_migrations.mkdir()
    shutil.copyfile(
        MIGRATIONS_DIRECTORY / "0001_init.sql",
        prior_migrations / "0001_init.sql",
    )
    database_path = tmp_path / "phase8.db"
    connection = connect_database(database_path)
    try:
        assert run_migrations(connection, prior_migrations) == 1
        connection.execute(
            "INSERT INTO profiles(id, display_name, created_at) VALUES (?, ?, ?)",
            ("profile-1", "Student", "2026-10-17T06:00:00.000Z"),
        )
        connection.execute(
            "INSERT INTO question_sets(id, version, title, subject, chapter, marking_json, "
            "content_hash, downloaded_at, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "set-1",
                1,
                "Set",
                "Biology",
                "Chapter",
                '{"correct":4,"skip":0,"wrong":-1}',
                "sha256:test",
                "2026-10-17T06:00:00.000Z",
                1,
            ),
        )
        connection.execute(
            "INSERT INTO questions(set_id, set_version, id, position, topic, difficulty, "
            "question_text, options_json, correct_key) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "set-1",
                1,
                "q1",
                1,
                "Topic",
                1,
                "Question?",
                '[{"key":"A","text":"A"},{"key":"B","text":"B"},'
                '{"key":"C","text":"C"},{"key":"D","text":"D"}]',
                "A",
            ),
        )
        connection.execute(
            "INSERT INTO attempts(id, profile_id, set_id, set_version, status, started_at, "
            "completed_at, duration_ms, score, sync_status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "attempt-1",
                "profile-1",
                "set-1",
                1,
                "completed",
                "2026-10-17T06:00:00.000Z",
                "2026-10-17T06:10:00.000Z",
                600000,
                4,
                "pending",
            ),
        )
        connection.execute(
            "INSERT INTO attempt_questions(attempt_id, position, question_id) VALUES (?, ?, ?)",
            ("attempt-1", 1, "q1"),
        )
        connection.execute(
            "INSERT INTO responses(id, attempt_id, question_id, selected_key, confidence, "
            "is_correct, response_time_ms) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("response-1", "attempt-1", "q1", "A", "sure", 1, 1000),
        )
    finally:
        connection.close()

    with Repository(database_path) as repository:
        assert repository.schema_version == 7
        assert repository.get_profile("profile-1") is not None
        assert repository.get_question_set("set-1", 1) is not None
        assert repository.get_attempt("attempt-1") is not None
        assert repository.get_response("attempt-1", "q1") is not None
        state = repository.get_attempt_sync_state("attempt-1")
        assert state.status.value == "pending"
        assert state.next_sync_at is None
