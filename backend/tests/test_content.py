import json
from pathlib import Path

import pytest

from backend.app.services.content import (
    PackVersionConflict,
    publish_pack_bytes,
    resolve_storage_path,
)


def sample_bytes() -> bytes:
    return Path("content/sample_biology.json").read_bytes()


def publish(client, data: bytes | None = None):
    with client.app.state.session_factory() as session:
        return publish_pack_bytes(
            data or sample_bytes(),
            session=session,
            storage_root=client.app.state.settings.content_storage_path,
        )


def test_authenticated_catalog_is_deterministic_and_hides_storage(client, auth_headers) -> None:
    original = json.loads(sample_bytes())
    second = json.loads(sample_bytes())
    second["set"]["id"] = "chemistry-atom-practice"
    second["set"]["subject"] = "Chemistry"
    second["set"]["title"] = "Atom Practice"
    second["set"]["chapter"] = "Atoms"
    publish(client, json.dumps(second).encode())
    publish(client, json.dumps(original).encode())

    response = client.get("/api/v1/content/catalog", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == 1
    assert [(row["subject"], row["set_id"]) for row in body["packs"]] == [
        ("Biology", "biology-cell-practice-01"),
        ("Chemistry", "chemistry-atom-practice"),
    ]
    assert all("storage_path" not in row for row in body["packs"])


def test_catalog_and_download_require_valid_device_credential(client) -> None:
    assert client.get("/api/v1/content/catalog").status_code == 401
    assert (
        client.get(
            "/api/v1/content/packs/biology-cell-practice-01/1",
            headers={"Authorization": "Bearer invalid"},
        ).status_code
        == 401
    )


def test_download_returns_exact_published_bytes_and_metadata(client, auth_headers) -> None:
    data = sample_bytes()
    result = publish(client, data)

    response = client.get(
        f"/api/v1/content/packs/{result.pack.set_id}/{result.pack.version}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.content == data
    assert response.headers["content-type"].startswith("application/json")
    assert int(response.headers["content-length"]) == len(data)
    assert response.headers["x-content-sha256"] == result.pack.sha256


def test_unknown_pack_is_404_without_latest_substitution(client, auth_headers) -> None:
    publish(client)
    response = client.get(
        "/api/v1/content/packs/biology-cell-practice-01/999", headers=auth_headers
    )
    assert response.status_code == 404


def test_conflicting_duplicate_version_is_rejected(client) -> None:
    publish(client)
    changed = json.loads(sample_bytes())
    changed["set"]["title"] = "Conflicting immutable title"
    with pytest.raises(PackVersionConflict):
        publish(client, json.dumps(changed).encode())


def test_catalog_exposes_multiple_exact_versions(client, auth_headers) -> None:
    first = json.loads(sample_bytes())
    second = json.loads(sample_bytes())
    second["set"]["version"] = 2
    publish(client, json.dumps(second).encode())
    publish(client, json.dumps(first).encode())
    response = client.get("/api/v1/content/catalog", headers=auth_headers)
    assert [row["version"] for row in response.json()["packs"]] == [1, 2]


@pytest.mark.parametrize("unsafe", ["../pack.json", "/tmp/pack.json", "C:\\pack.json"])
def test_storage_path_rejects_traversal_and_absolute_paths(tmp_path, unsafe) -> None:
    with pytest.raises(ValueError):
        resolve_storage_path(tmp_path, unsafe)
