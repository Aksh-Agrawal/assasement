"""FastAPI application factory and default development app."""

from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI

from backend.app.api.routes import attempts, content, health, pairing, updates
from backend.app.config import Settings
from backend.app.db.models import Base
from backend.app.db.session import create_database_engine, create_session_factory


def create_app(
    settings: Settings | None = None,
    *,
    clock: Callable[[], datetime] | None = None,
) -> FastAPI:
    resolved = settings or Settings.from_environment()
    engine = create_database_engine(resolved.database_url)

    @asynccontextmanager
    async def lifespan(_application: FastAPI):
        # SQLite remains a zero-setup test/smoke mode. PostgreSQL schema is Alembic-owned.
        if engine.dialect.name == "sqlite":
            Base.metadata.create_all(engine)
        yield
        engine.dispose()

    application = FastAPI(
        title="Assessment Sync Development Backend", version="0.1.0", lifespan=lifespan
    )
    application.state.settings = resolved
    application.state.engine = engine
    application.state.session_factory = create_session_factory(engine)
    application.state.clock = clock or (lambda: datetime.now(UTC))
    application.include_router(health.router)
    application.include_router(pairing.router)
    application.include_router(updates.router)
    application.include_router(content.router)
    application.include_router(attempts.router)
    return application


app = create_app()
