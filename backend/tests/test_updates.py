"""Authenticated development update catalog endpoints."""

import base64
import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import create_app
from backend.tests.conftest import TOKEN, issue_test_credential


def test_update_metadata_and_artifact_require_device_auth(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog"
    catalog.mkdir()
    artifact = catalog / "assessment-device-0.2.0.tar.gz"
    artifact.write_bytes(b"signed elsewhere")
    manifest = {
        "release": {"version": "0.2.0"},
        "artifact": {"filename": artifact.name},
    }
    (catalog / "update-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (catalog / "update-manifest.sig").write_bytes(b"signature")
    database_url = f"sqlite:///{(tmp_path / 'updates.db').as_posix()}"
    app = create_app(Settings(database_url=database_url, update_catalog_directory=catalog))
    with TestClient(app) as client:
        issue_test_credential(app)
        assert client.get("/api/v1/device-updates/latest").status_code == 401
        headers = {"Authorization": f"Bearer {TOKEN}"}
        response = client.get("/api/v1/device-updates/latest", headers=headers)
        assert response.status_code == 200
        assert response.json() == {
            "manifest": manifest,
            "signature": base64.b64encode(b"signature").decode("ascii"),
        }
        download = client.get("/api/v1/device-updates/0.2.0/artifact", headers=headers)
        assert download.status_code == 200 and download.content == artifact.read_bytes()
