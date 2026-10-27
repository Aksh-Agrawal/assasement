"""Authenticated content catalog and exact-byte pack downloads."""

from datetime import UTC
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.dependencies import (
    AuthenticatedDevice,
    authenticate_device,
    database_session,
)
from backend.app.db.models import QuestionPack
from backend.app.services.content import resolve_storage_path

router = APIRouter(prefix="/api/v1/content", tags=["content"])


@router.get("/catalog")
def catalog(
    _device: Annotated[AuthenticatedDevice, Depends(authenticate_device)],
    session: Annotated[Session, Depends(database_session)],
) -> dict:
    rows = session.scalars(
        select(QuestionPack)
        .where(QuestionPack.is_active.is_(True))
        .order_by(QuestionPack.subject, QuestionPack.set_id, QuestionPack.version)
    ).all()
    return {
        "schema_version": 1,
        "packs": [
            {
                "set_id": row.set_id,
                "version": row.version,
                "title": row.title,
                "subject": row.subject,
                "chapter": row.chapter,
                "question_count": row.question_count,
                "size_bytes": row.size_bytes,
                "sha256": row.sha256,
                "published_at": (
                    row.published_at.replace(tzinfo=UTC)
                    if row.published_at.tzinfo is None
                    else row.published_at
                ),
            }
            for row in rows
        ],
    }


@router.get("/packs/{set_id}/{version}", response_class=FileResponse)
def download_pack(
    set_id: str,
    version: int,
    request: Request,
    _device: Annotated[AuthenticatedDevice, Depends(authenticate_device)],
    session: Annotated[Session, Depends(database_session)],
) -> FileResponse:
    row = session.scalar(
        select(QuestionPack).where(
            QuestionPack.set_id == set_id,
            QuestionPack.version == version,
            QuestionPack.is_active.is_(True),
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Question pack not found")
    try:
        artifact = resolve_storage_path(request.app.state.settings.content_storage_path, row.storage_path)
    except ValueError as error:
        raise HTTPException(status_code=404, detail="Question pack not found") from error
    if not artifact.is_file():
        raise HTTPException(status_code=404, detail="Question pack not found")
    return FileResponse(
        artifact,
        media_type="application/json",
        headers={"ETag": f'"sha256:{row.sha256}"', "X-Content-SHA256": row.sha256},
    )
