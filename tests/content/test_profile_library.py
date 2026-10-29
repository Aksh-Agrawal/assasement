import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from app.assessment import AssessmentApplication
from app.content.catalog import RemotePack
from app.content.client import ContentApiClient, ContentAuthError, ContentNetworkError
from app.content.profile_library import download_for_profile, refresh_library
from app.core.models import Profile
from app.data.db import MIGRATIONS_DIRECTORY, connect_database, run_migrations
from app.data.repo import Repository
from app.input.actions import Action
from app.ui.controller import UIController
from app.ui.router import UIScreen


def setup(repo):
    repo.create_profile(Profile("a", "Student A"))
    repo.create_profile(Profile("b", "Student B"))
    repo.apply_profile_link("a", {
        "local_profile_id": "a", "link_id": str(uuid4()), "student_account_id": str(uuid4()),
        "study_profile_id": str(uuid4()), "account_display_name": "A",
        "study_profile_name": "NEET", "status": "linked",
    })
    repo.apply_profile_link("b", {
        "local_profile_id": "b", "link_id": str(uuid4()), "student_account_id": repo.get_profile("a").cloud_account_id,
        "study_profile_id": str(uuid4()), "account_display_name": "A",
        "study_profile_name": "JEE", "status": "linked",
    })
    repo.cache_student_account_context(repo.get_profile("a").cloud_account_id, "A")
    repo.set_setting("account_profiles", json.dumps({"profiles": [{"local_profile_id": "a"}, {"local_profile_id": "b"}], "profile_count": 2}))
    return repo.get_profile_link_context("a")["link_id"]


def metadata(data):
    pack = json.loads(data)
    return {"set_id": pack["set"]["id"], "version": pack["set"]["version"],
        "title": pack["set"]["title"], "subject": pack["set"]["subject"],
        "chapter": pack["set"]["chapter"], "question_count": len(pack["questions"]),
        "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
        "published_at": datetime.now(UTC).isoformat()}


def transport(state):
    def handle(request):
        if state.get("offline"):
            raise httpx.ConnectError("network down", request=request)
        if state.get("revoked"):
            return httpx.Response(403)
        if request.url.path.endswith("/catalog"):
            return httpx.Response(200, json={"schema_version": 1, "packs": state["packs"], "next_offset": None})
        if request.url.path.endswith("/status"):
            state.setdefault("acks", []).append(json.loads(request.content))
            return httpx.Response(200, json={"status": "downloaded"})
        return httpx.Response(200, content=state["data"])
    return httpx.MockTransport(handle)


def test_download_offline_switching_removal_and_pinned_version(tmp_path):
    path = tmp_path / "pi.db"
    data = Path("content/sample_biology.json").read_bytes()
    pack = metadata(data)
    state = {"data": data, "packs": [pack]}
    with Repository(path) as repo:
        link = setup(repo)
        with ContentApiClient("https://cloud.test", auth_token="device", link_id=link,
                              local_profile_id="a", transport=transport(state)) as client:
            refresh_library(repo, client, "a", link)
            assert repo.visible_question_sets("a") == ()
            result = download_for_profile(repo, client, "a", link, RemotePack.from_dict(pack),
                temp_directory=tmp_path, max_pack_bytes=10**6)
            assert result.status.value == "INSTALLED"
            assert state["acks"][-1]["status"] == "downloaded"
            assert len(repo.visible_question_sets("a")) == 1
            assert repo.visible_question_sets("b") == ()
            with pytest.raises(ValueError, match="selected profile"):
                AssessmentApplication(repo).start_test("b", pack["set_id"], 1)
            state["offline"] = True
            with pytest.raises(ContentNetworkError):
                refresh_library(repo, client, "a", link)
            app = AssessmentApplication(repo)
            attempt = app.start_test("a", pack["set_id"], 1)
            order = repo.get_attempt_question_order(attempt.id)
            app.select_answer("A")
            app.continue_unrated()
            app.pause()
            state["offline"] = False
            new = json.loads(data)
            new["set"]["version"] = 2
            state["data"] = json.dumps(new).encode()
            state["packs"] = [metadata(state["data"])]
            result = download_for_profile(repo, client, "a", link,
                RemotePack.from_dict(state["packs"][0]), temp_directory=tmp_path, max_pack_bytes=10**6)
            assert result.status.value == "INSTALLED"
            resumed = AssessmentApplication(repo)
            assert resumed.resume_attempt("a").set_version == 1
            assert repo.get_attempt_question_order(attempt.id) == order
            state["packs"] = []
            refresh_library(repo, client, "a", link)
            assert repo.visible_question_sets("a") == ()
            # Removal does not erase current work, exact bytes or review history.
            assert AssessmentApplication(repo).resume_attempt("a").set_version == 1
            assert repo.get_question_set(pack["set_id"], 1) is not None
            assert repo.get_question_set(pack["set_id"], 2) is not None
    with Repository(path) as repo:
        assert repo.visible_question_sets("b") == ()
        assert repo.get_attempt(attempt.id).set_version == 1


@pytest.mark.parametrize("failure", ["hash", "schema"])
def test_existing_validator_rejects_bad_profile_download_without_granting_bytes(tmp_path, failure):
    data = Path("content/sample_biology.json").read_bytes()
    item = metadata(data)
    if failure == "hash":
        body = data.replace(b"Cell", b"Fail", 1)
    else:
        bad = json.loads(data)
        bad["questions"][0]["options"] = []
        body = json.dumps(bad).encode()
        item["size_bytes"], item["sha256"] = len(body), hashlib.sha256(body).hexdigest()
    state = {"data": body, "packs": [item]}
    with Repository(tmp_path / "db") as repo:
        link = setup(repo)
        with ContentApiClient("https://cloud.test", auth_token="device", link_id=link,
                              local_profile_id="a", transport=transport(state)) as client:
            result = download_for_profile(repo, client, "a", link, RemotePack.from_dict(item),
                temp_directory=tmp_path, max_pack_bytes=10**6)
            assert result.status.value in {"HASH_MISMATCH", "VALIDATION_FAILED"}
            assert repo.list_question_sets() == ()
            assert state["acks"][-1]["status"] == "failed"


def test_deduplication_exact_profile_ui_and_revocation(tmp_path):
    data = Path("content/sample_biology.json").read_bytes()
    item = metadata(data)
    state = {"data": data, "packs": [item]}
    with Repository(tmp_path / "db") as repo:
        link = setup(repo)
        with ContentApiClient("https://cloud.test", auth_token="device", link_id=link,
                              local_profile_id="a", transport=transport(state)) as client:
            download_for_profile(repo, client, "a", link, RemotePack.from_dict(item),
                temp_directory=tmp_path, max_pack_bytes=10**6)
            result = download_for_profile(repo, client, "a", link, RemotePack.from_dict(item),
                temp_directory=tmp_path, max_pack_bytes=10**6)
            assert result.status.value == "ALREADY_PRESENT"
            assert len(repo.list_question_sets()) == 1
            c = UIController(repo, startup=True)
            c.finish_splash()
            c.handle(Action.CONFIRM, ("choice", 0))
            assert len(c.question_sets) == 1
            c.route(UIScreen.PROFILE)
            c.handle(Action.CONFIRM, ("choice", 1))
            assert c.question_sets == ()
            assert c.remote_packs == ()
            state["revoked"] = True
            with pytest.raises(ContentAuthError):
                refresh_library(repo, client, "a", link)
            assert repo.visible_question_sets("a") == ()
            assert repo.list_question_sets()


def test_v4_migration_keeps_shared_legacy_profiles_and_content(tmp_path):
    old = tmp_path / "migrations"
    old.mkdir()
    for path in MIGRATIONS_DIRECTORY.glob("*.sql"):
        if path.name < "0005":
            shutil.copyfile(path, old / path.name)
    path = tmp_path / "db"
    con = connect_database(path)
    assert run_migrations(con, old) == 4
    con.execute("INSERT INTO profiles(id,display_name,created_at) VALUES ('old','Old','2026-10-28T00:00:00Z')")
    assert run_migrations(con) == 6
    assert run_migrations(con) == 6
    con.close()
    with Repository(path) as repo:
        assert repo.get_profile("old").ownership_state == "legacy_unclaimed"
        assert repo.profile_library_catalog("old") == []


def test_two_explicit_profiles_share_one_physical_pack_with_independent_grants(tmp_path):
    data = Path("content/sample_biology.json").read_bytes()
    item = metadata(data)
    state = {"data": data, "packs": [item]}
    with Repository(tmp_path / "db") as repo:
        link_a = setup(repo)
        link_b = repo.get_profile_link_context("b")["link_id"]
        for local, link in (("a", link_a), ("b", link_b)):
            with ContentApiClient("https://cloud.test", auth_token="device", link_id=link,
                                  local_profile_id=local, transport=transport(state)) as client:
                result = download_for_profile(repo, client, local, link, RemotePack.from_dict(item),
                    temp_directory=tmp_path, max_pack_bytes=10**6)
                assert result.status.value == ("INSTALLED" if local == "a" else "ALREADY_PRESENT")
        assert len(repo.list_question_sets()) == 1
        assert len(repo.visible_question_sets("a")) == len(repo.visible_question_sets("b")) == 1
        repo.cache_profile_library("a", link_a, [])
        assert repo.visible_question_sets("a") == ()
        assert len(repo.visible_question_sets("b")) == 1
        assert len(repo.list_question_sets()) == 1


def test_background_delivery_budget_rotates_between_profile_jobs(tmp_path):
    from app.config import AppConfig
    from app.content.profile_library import sync_profile_deliveries
    data = Path("content/sample_biology.json").read_bytes()
    item = metadata(data)
    state = {"data": data, "packs": [item]}
    with Repository(tmp_path / "db") as repo:
        setup(repo)
        class Api:
            def content(self, *, local_profile_id, link_id):
                return ContentApiClient("https://cloud.test", auth_token="device",
                    link_id=link_id, local_profile_id=local_profile_id, transport=transport(state))
        config = AppConfig(content_max_downloads_per_cycle=1, content_download_directory=tmp_path)
        sync_profile_deliveries(repo, Api(), config)
        assert [a["local_profile_id"] for a in state["acks"]] == ["a"]
        sync_profile_deliveries(repo, Api(), config)
        assert [a["local_profile_id"] for a in state["acks"]] == ["a", "b"]
        assert len(repo.list_question_sets()) == 1


def test_download_auth_rejection_revokes_cached_profile_eligibility(tmp_path):
    data = Path("content/sample_biology.json").read_bytes()
    item = metadata(data)
    def handler(request):
        if request.url.path.endswith("/catalog"):
            return httpx.Response(200, json={"schema_version": 1, "packs": [item]})
        return httpx.Response(403)
    with Repository(tmp_path / "db") as repo:
        link = setup(repo)
        with ContentApiClient("https://cloud.test", auth_token="device", link_id=link,
                              local_profile_id="a", transport=httpx.MockTransport(handler)) as client:
            result = download_for_profile(repo, client, "a", link, RemotePack.from_dict(item),
                temp_directory=tmp_path, max_pack_bytes=10**6)
            assert result.status.value == "AUTH_REQUIRED"
            assert repo.profile_library_catalog("a") == []
