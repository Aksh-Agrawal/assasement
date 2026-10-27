from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from backend.app.db.session import create_database_engine


def test_fresh_sqlite_migration_and_repeat_upgrade(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'migration.db').as_posix()}"
    config = Config("backend/alembic.ini")
    config.attributes["database_url"] = database_url

    command.upgrade(config, "head")
    command.upgrade(config, "head")

    engine = create_database_engine(database_url)
    inspector = inspect(engine)
    assert {
        "alembic_version", "attempts", "attempt_responses", "devices",
        "pairing_sessions", "device_credentials",
    } <= set(
        inspector.get_table_names()
    )
    engine.dispose()
