import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import httpx

from app.content.catalog import RemotePack
from app.content.client import ContentApiClient
from app.content.validator import SUPPORTED_SCHEMA_VERSION


def test_profile_figure_fetch_uses_link_and_checks_exact_png_digest() -> None:
    image = b"\x89PNG\r\n\x1a\nfigure"
    digest = sha256(image).hexdigest()
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["query"] = dict(request.url.params)
        seen["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, content=image)

    pack = RemotePack.from_dict({
        "set_id": "bio-pack", "version": 2, "title": "Biology", "subject": "Biology",
        "chapter": "Cells", "question_count": 1, "size_bytes": 100,
        "sha256": "b" * 64, "published_at": datetime.now(UTC).isoformat(),
    })
    with ContentApiClient("https://cloud.example", auth_token="device-token",
                          local_profile_id="local-profile", link_id="link-uuid",
                          transport=httpx.MockTransport(handler)) as client:
        result = client.fetch_figure(pack, f"media/{digest}.png")

    assert result == image
    assert seen["path"] == f"/api/v1/profile-content/link-uuid/packs/bio-pack/2/figures/{digest}"
    assert seen["query"] == {"local_profile_id": "local-profile"}
    assert seen["auth"] == "Bearer device-token"


def test_profile_operations_catalog_and_download_request_supported_pack_schema() -> None:
    data = Path("content/sample_biology.json").read_bytes()
    document = json.loads(data)
    pack = document["set"]
    item = {
        "set_id": pack["id"], "version": pack["version"], "title": pack["title"],
        "subject": pack["subject"], "chapter": pack["chapter"],
        "question_count": len(document["questions"]), "size_bytes": len(data),
        "sha256": sha256(data).hexdigest(), "published_at": datetime.now(UTC).isoformat(),
    }
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/operations"):
            return httpx.Response(200, json={"snapshot_token": "snapshot", "removals": []})
        if request.url.path.endswith("/catalog"):
            return httpx.Response(200, json={
                "schema_version": 1, "packs": [item], "next_offset": None,
            })
        return httpx.Response(200, content=data)

    with ContentApiClient("https://cloud.example", auth_token="device-token",
                          local_profile_id="local-profile", link_id="link-uuid",
                          transport=httpx.MockTransport(handler)) as client:
        assert client.fetch_changes()["snapshot_token"] == "snapshot"
        remote = client.fetch_catalog().packs[0]
        with client.stream_pack(remote) as response:
            assert response.read() == data

    assert [request.url.params.get("pack_schema") for request in requests] == [
        str(SUPPORTED_SCHEMA_VERSION), str(SUPPORTED_SCHEMA_VERSION), str(SUPPORTED_SCHEMA_VERSION),
    ]
    assert all(request.url.params.get("local_profile_id") == "local-profile"
               for request in requests)


def test_profile_pack_becomes_playable_only_after_figures_verify(tmp_path):
    from app.content.profile_library import download_for_profile
    from app.content.sync import ContentSyncStatus
    from app.data.repo import Repository
    from tests.content.test_profile_library import metadata, setup

    image = b"\x89PNG\r\n\x1a\nfigure"
    reference = f"media/{sha256(image).hexdigest()}.png"
    pack = json.loads(Path("content/sample_biology.json").read_bytes())
    pack["questions"][0]["media_ref"] = reference
    data = json.dumps(pack).encode()
    item = metadata(data)
    figure_ready = False

    def handle(request):
        if request.url.path.endswith("/catalog"):
            return httpx.Response(200, json={"schema_version": 1, "packs": [item], "next_offset": None})
        if request.url.path.endswith("/status"):
            return httpx.Response(200, json={})
        if "/figures/" in request.url.path:
            assert not repo.visible_question_sets("a")
            return httpx.Response(200, content=image if figure_ready else b"corrupt")
        return httpx.Response(200, content=data)

    with Repository(tmp_path / "figures.db") as repo:
        link = setup(repo)
        with ContentApiClient("https://cloud.test", auth_token="device", link_id=link,
                              local_profile_id="a", transport=httpx.MockTransport(handle)) as client:
            remote = RemotePack.from_dict(item)
            options = {"temp_directory": tmp_path, "max_pack_bytes": 10**6, "media_directory": tmp_path}
            assert download_for_profile(repo, client, "a", link, remote,
                                        **options).status is ContentSyncStatus.FAILED_DOWNLOAD
            assert not repo.visible_question_sets("a")
            assert repo.get_question_set(remote.set_id, remote.version) is None
            figure_ready = True
            assert download_for_profile(repo, client, "a", link, remote,
                                        **options).status is ContentSyncStatus.INSTALLED
            assert (tmp_path / reference).read_bytes() == image
            assert len(repo.visible_question_sets("a")) == 1
