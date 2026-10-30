import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from app.assessment import AssessmentApplication
from app.content.importer import import_pack
from app.content.validator import PackValidationError, validate_pack_bytes
from app.core.models import Profile
from app.data import db
from app.data.repo import Repository
from tests.content.test_profile_library import metadata, setup


@pytest.mark.parametrize("subject", ["Mathematics", "Physics", "English", "Computer Science", "History", "Hindi"])
def test_custom_subject_import_start_and_resume(tmp_path, subject):
    pack = json.loads(Path("content/sample_biology.json").read_bytes())
    pack["set"]["subject"] = subject
    file = tmp_path / "pack.json"
    file.write_text(json.dumps(pack), encoding="utf-8")
    with Repository(tmp_path / "pi.db") as repo:
        repo.create_profile(Profile("a", "Student"))
        imported = import_pack(file, repo).pack.question_set
        assert repo.visible_question_sets("a")[0].subject == subject
        app = AssessmentApplication(repo)
        attempt = app.start_test("a", imported.id, 1)
        assert app.resume_attempt("a").id == attempt.id


@pytest.mark.parametrize("subject", ["", "   ", "\t\n", "x" * 65])
def test_empty_or_overlong_subject_rejected(subject):
    pack = json.loads(Path("content/sample_biology.json").read_bytes())
    pack["set"]["subject"] = subject
    with pytest.raises(PackValidationError):
        validate_pack_bytes(json.dumps(pack).encode())


def test_v6_upgrade_preserves_content_history_links_and_foreign_keys(tmp_path, monkeypatch):
    old = tmp_path / "old_migrations"
    old.mkdir()
    for file in db.MIGRATIONS_DIRECTORY.glob("*.sql"):
        if file.name < "0007":
            shutil.copyfile(file, old / file.name)
    path = tmp_path / "pi.db"
    with monkeypatch.context() as patch:
        patch.setattr("app.data.repo.run_migrations", lambda connection: db.run_migrations(connection, old))
        with Repository(path) as repo:
            assert repo.schema_version == 6
            link = setup(repo)
            file = Path("content/sample_biology.json")
            pack = import_pack(file, repo, profile_only=True).pack.question_set
            repo.cache_profile_library("a", link, [metadata(file.read_bytes())])
            app = AssessmentApplication(repo)
            completed = app.start_test("a", pack.id, 1)
            app.request_submit()
            app.submit()
            partial = app.start_test("a", pack.id, 1)
            tables = ("question_sets", "questions", "private_pack_versions", "profile_library",
                      "attempts", "attempt_questions", "responses", "attempt_ownership")
            before = {table: [tuple(row) for row in repo._connection.execute("SELECT * FROM " + table)]
                      for table in tables}
    with Repository(path) as repo:
        assert repo.schema_version == 7
        for table in tables:
            assert [tuple(row) for row in repo._connection.execute("SELECT * FROM " + table)] == before[table]
        assert repo._connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert repo._connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert repo.quick_check().ok
        assert repo.get_attempt(completed.id).status.value == "completed"
        assert repo.find_in_progress_attempt("a").id == partial.id
        assert db.run_migrations(repo._connection) == 7
        assert repo._connection.execute("SELECT count(*) FROM sqlite_master WHERE type='trigger' AND name='question_sets_immutable_content'").fetchone()[0] == 1


def test_failed_table_rebuild_rolls_back_and_restores_fk_enforcement(tmp_path):
    migrations = tmp_path / "migrations"
    shutil.copytree(db.MIGRATIONS_DIRECTORY, migrations)
    (migrations / "0008_failure.sql").write_text(
        "-- requires_foreign_keys_off\nDROP TABLE question_sets;\nSELECT * FROM nonexistent_table;",
        encoding="utf-8")
    with Repository(tmp_path / "failure.db") as repo:
        pack = import_pack(Path("content/sample_biology.json"), repo).pack.question_set
        with pytest.raises(sqlite3.OperationalError):
            db.run_migrations(repo._connection, migrations)
        assert repo.schema_version == 7
        assert repo.get_question_set(pack.id, 1) == pack
        assert repo._connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert repo._connection.execute("PRAGMA foreign_key_check").fetchall() == []
