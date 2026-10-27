import json
from hashlib import sha256
from pathlib import Path

import httpx
import pytest

from app.assessment import AssessmentApplication
from app.content.catalog import Availability, ContentCatalog, compare_catalog
from app.content.client import ContentApiClient
from app.content.downloader import download_pack_to_temp
from app.content.importer import import_pack
from app.content.sync import ContentSyncStatus, sync_content_once
from app.core.models import Profile
from app.data.repo import Repository
from tests.faults.harness import FaultInjector, InjectedCrash


def pack_bytes(version: int = 1, *, changed: bool = False) -> bytes:
    value = json.loads(Path("content/sample_biology.json").read_bytes())
    value["set"]["version"] = version
    if changed:
        value["questions"][0]["question_text"] = f"Version {version} question text"
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


def remote(data: bytes, version: int = 1, *, size: int | None = None, digest: str | None = None):
    value = json.loads(data)
    metadata = value["set"]
    return {
        "set_id": metadata["id"],
        "version": version,
        "title": metadata["title"],
        "subject": metadata["subject"],
        "chapter": metadata["chapter"],
        "question_count": len(value["questions"]),
        "size_bytes": len(data) if size is None else size,
        "sha256": digest or sha256(data).hexdigest(),
        "published_at": "2026-10-19T00:00:00Z",
    }


def client_for(entries, downloads, *, catalog_status: int = 200) -> ContentApiClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/content/catalog":
            return httpx.Response(
                catalog_status,
                json={"schema_version": 1, "packs": entries},
            )
        parts = request.url.path.split("/")
        identity = (parts[-2], int(parts[-1]))
        return httpx.Response(200, content=downloads[identity])

    return ContentApiClient(
        "https://content.test",
        auth_token="device_test.secret",
        transport=httpx.MockTransport(handler),
    )


def run_sync(repository, client, tmp_path, **options):
    return sync_content_once(
        repository,
        client,
        temp_directory=tmp_path / "downloads",
        max_pack_bytes=25 * 1024 * 1024,
        max_downloads_per_cycle=options.pop("limit", 5),
        **options,
    )


def test_catalog_comparison_identifies_present_and_new_versions(tmp_path) -> None:
    v1 = pack_bytes()
    with Repository(tmp_path / "device.db") as repository:
        path = tmp_path / "v1.json"
        path.write_bytes(v1)
        import_pack(path, repository)
        catalog = ContentCatalog.from_dict(
            {"schema_version": 1, "packs": [remote(v1), remote(pack_bytes(2), 2)]}
        )
        result = compare_catalog(catalog, repository)
        assert [item.availability for item in result] == [
            Availability.ALREADY_INSTALLED,
            Availability.NEW_VERSION,
        ]


def test_successful_sync_imports_and_activates_new_version(tmp_path) -> None:
    v2 = pack_bytes(2, changed=True)
    with Repository(tmp_path / "device.db") as repository, client_for(
        [remote(v2, 2)], {("biology-cell-practice-01", 2): v2}
    ) as client:
        result = run_sync(repository, client, tmp_path)
        assert result.packs[0].status is ContentSyncStatus.INSTALLED
        assert repository.get_question_set("biology-cell-practice-01", 2) is not None
        assert repository.get_active_question_set("biology-cell-practice-01").version == 2


@pytest.mark.parametrize("mode", ["hash", "truncated", "invalid"])
def test_bad_download_never_changes_installed_content(tmp_path, mode) -> None:
    v1 = pack_bytes()
    v2 = pack_bytes(2, changed=True)
    entry = remote(v2, 2)
    delivered = v2
    expected = ContentSyncStatus.HASH_MISMATCH
    if mode == "hash":
        entry = remote(v2, 2, digest="0" * 64)
    elif mode == "truncated":
        delivered = v2[:-10]
        expected = ContentSyncStatus.FAILED_DOWNLOAD
    else:
        invalid = json.loads(v2)
        invalid["questions"][0]["correct_key"] = "X"
        delivered = json.dumps(invalid).encode()
        entry = remote(delivered, 2)
        expected = ContentSyncStatus.VALIDATION_FAILED
    with Repository(tmp_path / "device.db") as repository:
        local = tmp_path / "v1.json"
        local.write_bytes(v1)
        import_pack(local, repository)
        with client_for([entry], {(entry["set_id"], 2): delivered}) as client:
            result = run_sync(repository, client, tmp_path)
        assert result.packs[0].status is expected
        assert repository.get_question_set(entry["set_id"], 2) is None
        assert repository.get_active_question_set(entry["set_id"]).version == 1
        assert list((tmp_path / "downloads").glob("*")) == []


def test_import_failure_rolls_back_and_preserves_old_version(tmp_path) -> None:
    v1 = pack_bytes()
    v2 = pack_bytes(2, changed=True)

    armed = False

    def fail(point: str) -> None:
        if armed and point == "BEFORE_PACK_IMPORT_COMMIT":
            raise RuntimeError("injected import failure")

    with Repository(tmp_path / "device.db", fault_hook=fail) as repository:
        local = tmp_path / "v1.json"
        local.write_bytes(v1)
        import_pack(local, repository)
        armed = True
        with client_for([remote(v2, 2)], {("biology-cell-practice-01", 2): v2}) as client:
            result = run_sync(repository, client, tmp_path)
        assert result.packs[0].status is ContentSyncStatus.IMPORT_FAILED
        assert repository.get_question_set("biology-cell-practice-01", 2) is None
        assert repository.get_active_question_set("biology-cell-practice-01").version == 1


def test_active_attempt_remains_pinned_when_new_version_arrives(tmp_path) -> None:
    database = tmp_path / "device.db"
    v1 = pack_bytes()
    v2 = pack_bytes(2, changed=True)
    local = tmp_path / "v1.json"
    local.write_bytes(v1)
    with Repository(database) as repository:
        import_pack(local, repository)
        student = repository.create_profile(Profile(id="student-1", display_name="Student"))
        application = AssessmentApplication(repository)
        attempt = application.start_test(student.id, "biology-cell-practice-01", 1, shuffle_seed=7)
        original_order = repository.get_attempt_question_order(attempt.id)
        original_text = repository.get_question(
            "biology-cell-practice-01", 1, original_order[0]
        ).question_text
        application.select_answer("A")
        with client_for([remote(v2, 2)], {("biology-cell-practice-01", 2): v2}) as client:
            run_sync(repository, client, tmp_path)

    with Repository(database) as repository:
        resumed = AssessmentApplication(repository).resume_attempt(student.id)
        assert resumed is not None and resumed.set_version == 1
        assert repository.get_attempt_question_order(attempt.id) == original_order
        assert repository.get_question(
            "biology-cell-practice-01", 1, original_order[0]
        ).question_text == original_text
        assert repository.get_active_question_set("biology-cell-practice-01").version == 2


def test_offline_and_revoked_auth_are_non_blocking(tmp_path) -> None:
    v1 = pack_bytes()
    local = tmp_path / "v1.json"
    local.write_bytes(v1)
    with Repository(tmp_path / "device.db") as repository:
        import_pack(local, repository)
        offline = httpx.MockTransport(lambda request: (_ for _ in ()).throw(httpx.ConnectError("offline", request=request)))
        with ContentApiClient("https://offline.test", auth_token="device_x.y", transport=offline) as client:
            result = run_sync(repository, client, tmp_path)
        assert result.status is ContentSyncStatus.NETWORK_UNAVAILABLE
        with client_for([], {}, catalog_status=401) as client:
            result = run_sync(repository, client, tmp_path)
        assert result.status is ContentSyncStatus.AUTH_REQUIRED
        assert repository.get_question_set("biology-cell-practice-01", 1) is not None


def test_crash_during_import_rolls_back_and_temp_is_discarded(tmp_path) -> None:
    v2 = pack_bytes(2, changed=True)
    faults = FaultInjector()
    faults.arm("BEFORE_PACK_IMPORT_COMMIT")
    with Repository(tmp_path / "device.db", fault_hook=faults) as repository, client_for(
        [remote(v2, 2)], {("biology-cell-practice-01", 2): v2}
    ) as client:
        with pytest.raises(InjectedCrash):
            run_sync(repository, client, tmp_path)
        assert repository.get_question_set("biology-cell-practice-01", 2) is None
        assert list((tmp_path / "downloads").glob("*")) == []


def test_dry_run_and_batch_limit_do_not_overrun_cycle(tmp_path) -> None:
    v1 = pack_bytes()
    v2 = pack_bytes(2, changed=True)
    entries = [remote(v1), remote(v2, 2)]
    downloads = {
        ("biology-cell-practice-01", 1): v1,
        ("biology-cell-practice-01", 2): v2,
    }
    with Repository(tmp_path / "device.db") as repository, client_for(
        entries, downloads
    ) as client:
        dry = run_sync(repository, client, tmp_path, dry_run=True, limit=1)
        assert dry.eligible_count == 2
        assert [item.status for item in dry.packs] == [ContentSyncStatus.WOULD_DOWNLOAD]
        assert repository.list_question_sets() == ()
        installed = run_sync(repository, client, tmp_path, limit=1)
        assert [item.status for item in installed.packs] == [ContentSyncStatus.INSTALLED]
        assert repository.get_question_set("biology-cell-practice-01", 1) is not None
        assert repository.get_question_set("biology-cell-practice-01", 2) is None


def test_catalog_identity_must_match_downloaded_pack(tmp_path) -> None:
    actual_v1 = pack_bytes()
    lying_entry = remote(actual_v1, 2)
    with Repository(tmp_path / "device.db") as repository, client_for(
        [lying_entry], {("biology-cell-practice-01", 2): actual_v1}
    ) as client:
        result = run_sync(repository, client, tmp_path)
        assert result.packs[0].status is ContentSyncStatus.VALIDATION_FAILED
        assert repository.list_question_sets() == ()


def test_completed_download_without_import_leaves_database_unchanged(tmp_path) -> None:
    data = pack_bytes()
    pack = ContentCatalog.from_dict(
        {"schema_version": 1, "packs": [remote(data)]}
    ).packs[0]
    with Repository(tmp_path / "device.db") as repository, client_for(
        [remote(data)], {("biology-cell-practice-01", 1): data}
    ) as client:
        temporary = download_pack_to_temp(
            client,
            pack,
            temp_directory=tmp_path / "downloads",
            max_bytes=25 * 1024 * 1024,
        )
        assert temporary.name.startswith("pack-")
        assert repository.list_question_sets() == ()
        temporary.unlink()
