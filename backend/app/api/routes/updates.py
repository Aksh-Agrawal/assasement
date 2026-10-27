"""Authenticated development update catalog and artifact endpoints."""

import base64
import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse

from backend.app.api.dependencies import AuthenticatedDevice, authenticate_device

router = APIRouter(prefix="/api/v1/device-updates", tags=["updates"])


@router.get("/latest")
def latest_update(
    request: Request,
    _device: Annotated[AuthenticatedDevice, Depends(authenticate_device)],
) -> dict:
    directory = request.app.state.settings.update_catalog_directory
    manifest_path = directory / "update-manifest.json"
    signature_path = directory / "update-manifest.sig"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        signature = base64.b64encode(signature_path.read_bytes()).decode("ascii")
    except (OSError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=404, detail="No development update is published") from error
    return {"manifest": manifest, "signature": signature}


@router.get("/{version}/artifact", response_class=FileResponse)
def update_artifact(
    version: str,
    request: Request,
    _device: Annotated[AuthenticatedDevice, Depends(authenticate_device)],
) -> FileResponse:
    directory = request.app.state.settings.update_catalog_directory
    try:
        manifest = json.loads((directory / "update-manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=404, detail="Update not found") from error
    if manifest.get("release", {}).get("version") != version:
        raise HTTPException(status_code=404, detail="Update not found")
    filename = manifest.get("artifact", {}).get("filename", "")
    if not filename or filename != Path(filename).name:
        raise HTTPException(status_code=404, detail="Update not found")
    artifact = directory / filename
    if not artifact.is_file():
        raise HTTPException(status_code=404, detail="Update not found")
    return FileResponse(artifact, filename=filename, media_type="application/gzip")
