import shutil
from datetime import UTC, datetime
from uuid import uuid4

from app.auth.student_context import load_student_routing_context
from app.core.models import Profile
from app.data.db import MIGRATIONS_DIRECTORY, connect_database, run_migrations
from app.data.repo import Repository


def test_v2_migration_preserves_every_legacy_row_and_is_repeatable(tmp_path):
    old = tmp_path / "migrations"
    old.mkdir()
    for name in ("0001_init.sql", "0002_sync_retry.sql"):
        shutil.copyfile(MIGRATIONS_DIRECTORY / name, old / name)
    path = tmp_path / "existing.db"
    connection = connect_database(path)
    assert run_migrations(connection, old) == 2
    connection.execute(
        "INSERT INTO profiles(id, display_name, server_user_id, created_at) "
        "VALUES ('legacy', 'Student', 'arbitrary-legacy-string', '2026-10-17T06:00:00Z')"
    )
    before = tuple(connection.execute("SELECT * FROM profiles").fetchone())
    assert run_migrations(connection) == 6
    assert run_migrations(connection) == 6
    after = tuple(connection.execute("SELECT * FROM profiles").fetchone())
    assert after[:len(before)] == before
    connection.close()
    with Repository(path) as repo:
        legacy = repo.get_profile("legacy")
        assert legacy.cloud_account_id is None and legacy.cloud_profile_id is None
        assert legacy.ownership_state == "legacy_unclaimed"
        assert legacy.link_state == "unlinked"
        account = str(uuid4())
        repo.cache_student_account_context(account, "Account", last_verified_at=datetime.now(UTC))
        context = load_student_routing_context(repo)
        assert context.auth_state == "verification_required"
        assert context.offline_policy == "pending"
        assert context.legacy_profile_ids == ("legacy",)
        assert context.owned_profile_ids == ()
        assert repo.get_profile("legacy") == legacy
    with Repository(path) as repo:
        assert repo.get_student_account_context()["cloud_account_id"] == account
        repo.clear_student_account_context()
        assert repo.get_student_account_context() is None
        assert repo.get_profile("legacy") == legacy


def test_mapping_roundtrip_and_routing_never_treats_cache_as_authentication(tmp_path):
    account = str(uuid4())
    profile = Profile("local", "NEET", cloud_account_id=account, cloud_profile_id=str(uuid4()),
                      ownership_state="owned", link_state="linked")
    with Repository(tmp_path / "db") as repo:
        repo.create_profile(profile)
        assert repo.get_profile(profile.id) == profile
        assert load_student_routing_context(repo).owned_profile_ids == ()
        repo.cache_student_account_context(account, "Student")
        context = load_student_routing_context(repo)
        assert context.owned_profile_ids == ("local",)
        assert context.auth_state == "verification_required"
        repo.cache_student_account_context(str(uuid4()), "Other")
        assert load_student_routing_context(repo).owned_profile_ids == ()
        assert repo.get_profile("local") == profile
