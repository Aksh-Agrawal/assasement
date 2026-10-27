"""Integration tests for atomic immutable pack installation and assessment pinning."""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.assessment import AssessmentApplication
from app.content.importer import PackImportError, import_pack
from app.content.validator import PackValidationError
from app.core.models import Confidence, Profile
from app.data.repo import Repository

VALID_PACK = Path("tests/fixtures/packs/valid_20_questions.json")
INVALID_PACK = Path("tests/fixtures/packs/duplicate_question_id.json")
IMPORTED_AT = datetime(2026, 4, 5, 6, 7, 8, tzinfo=UTC)
PROFILE = Profile(id="550e8400-e29b-41d4-a716-446655440000", display_name="Student")


def make_version_2(tmp_path: Path) -> Path:
    data = json.loads(VALID_PACK.read_text(encoding="utf-8"))
    data["set"]["version"] = 2
    data["set"]["title"] = "Validator Test v2"
    data["questions"][0]["question_text"] = "Version 2 question 1"
    path = tmp_path / "version-2.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_import_persists_hash_timestamp_and_rejects_duplicate_version(tmp_path: Path) -> None:
    with Repository(tmp_path / "duplicate.db") as repository:
        result = import_pack(VALID_PACK, repository, now=IMPORTED_AT)
        metadata = repository.get_question_set_persistence(
            result.pack.summary.set_id, result.pack.summary.version
        )
        assert metadata is not None
        assert metadata.content_hash == result.pack.sha256
        assert metadata.downloaded_at == IMPORTED_AT
        assert metadata.is_active is True

        with pytest.raises(PackImportError) as captured:
            import_pack(VALID_PACK, repository)
        assert captured.value.code == "DUPLICATE_SET_VERSION"
        assert repository.get_question_set(
            result.pack.summary.set_id, result.pack.summary.version
        ) == result.pack.question_set


def test_validation_failure_does_not_change_database(tmp_path: Path) -> None:
    with Repository(tmp_path / "validation.db") as repository:
        imported = import_pack(VALID_PACK, repository)
        before_sets = repository.list_question_sets()
        before_active = repository.get_active_question_set(imported.pack.summary.set_id)

        with pytest.raises(PackValidationError):
            import_pack(INVALID_PACK, repository)

        assert repository.list_question_sets() == before_sets
        assert repository.get_active_question_set(imported.pack.summary.set_id) == before_active


def test_actual_insert_failure_rolls_back_and_preserves_active_v1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    version_2 = make_version_2(tmp_path)
    with Repository(tmp_path / "rollback.db") as repository:
        version_1 = import_pack(VALID_PACK, repository).pack.question_set
        original_insert = Repository._insert_question_rows

        def fail_after_first_row(
            connection: sqlite3.Connection,
            set_id: str,
            version: int,
            questions: object,
        ) -> None:
            original_insert(connection, set_id, version, tuple(questions)[:1])  # type: ignore[arg-type]
            raise sqlite3.IntegrityError("controlled Phase 5 failure")

        monkeypatch.setattr(
            Repository, "_insert_question_rows", staticmethod(fail_after_first_row)
        )
        with pytest.raises(sqlite3.IntegrityError, match="controlled"):
            import_pack(version_2, repository)

        assert repository.get_question_set(version_1.id, 2) is None
        assert repository.get_active_question_set(version_1.id) == version_1
        assert len(repository.get_questions(version_1.id, 1)) == 20


def test_multiple_versions_coexist_and_new_version_becomes_active(tmp_path: Path) -> None:
    version_2_path = make_version_2(tmp_path)
    with Repository(tmp_path / "versions.db") as repository:
        version_1 = import_pack(VALID_PACK, repository).pack.question_set
        version_2 = import_pack(version_2_path, repository).pack.question_set

        assert repository.list_question_set_versions(version_1.id) == (1, 2)
        assert repository.get_question_set(version_1.id, 1) == version_1
        assert repository.get_question_set(version_2.id, 2) == version_2
        assert repository.get_question_set(version_1.id, 1).questions[0].question_text == (  # type: ignore[union-attr]
            "Question 1"
        )
        assert repository.get_active_question_set(version_1.id) == version_2


def test_in_progress_attempt_stays_pinned_through_new_active_version(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "attempt-version.db"
    version_2_path = make_version_2(tmp_path)
    with Repository(database_path) as repository:
        version_1 = import_pack(VALID_PACK, repository).pack.question_set
        repository.create_profile(PROFILE, created_at=IMPORTED_AT)
        app = AssessmentApplication(repository)
        attempt = app.start_test(PROFILE.id, version_1.id, 1, shuffle_seed=31)
        order = repository.get_attempt_question_order(attempt.id)
        first_text = app.current_question().question_text
        app.select_answer(app.current_question().correct_key)
        app.set_confidence(Confidence.SURE)
        app.next_question()
        app.select_answer(app.current_question().correct_key)
        app.continue_unrated()
        app.next_question()
        app.pause()
        import_pack(version_2_path, repository)
        assert repository.get_active_question_set(version_1.id).version == 2  # type: ignore[union-attr]

    with Repository(database_path) as repository:
        app = AssessmentApplication(repository)
        resumed = app.resume_attempt(PROFILE.id)
        assert resumed is not None
        assert resumed.set_version == 1
        assert app.engine.question_set is not None
        assert app.engine.question_set.version == 1
        assert app.engine.ordered_question_ids == order
        assert app.engine.question_set.questions[0].question_text == "Question 1"
        assert first_text in {question.question_text for question in app.engine.question_set.questions}
        app.request_submit()
        result = app.submit()
        assert result.attempted == 2
        assert result.correct == 2
