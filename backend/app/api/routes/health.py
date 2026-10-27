"""Safe process liveness and database-backed readiness endpoints."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app import __version__

ALEMBIC_HEAD = "20261019_03"

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def readiness(request: Request):
    try:
        with request.app.state.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            if connection.dialect.name == "postgresql":
                revision = connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one()
                migration = "current" if revision == ALEMBIC_HEAD else "outdated"
            else:
                migration = "not_managed"
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "database": "unavailable",
                "version": __version__,
                "migration": "unknown",
            },
        )
    status_code = 200 if migration != "outdated" else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if status_code == 200 else "not_ready",
            "database": "ok",
            "version": __version__,
            "migration": migration,
        },
    )
