from pathlib import Path
from uuid import uuid4

import pytest

from app.assessment import AssessmentApplication
from app.content.client import ContentNetworkError
from app.content.institute_work import InstituteContentClient, download_work, refresh_work
from app.data.repo import Repository
from app.sync.payloads import build_upload_payload
from app.ui.controller import UIController
from app.ui.router import UIScreen
from tests.content.test_profile_library import metadata, setup, transport


def test_assignment_download_offline_resume_context_removal_and_privacy(tmp_path):
    data = Path("content/sample_biology.json").read_bytes()
    with Repository(tmp_path / "pi.db") as repo:
        link = setup(repo)
        p = repo.get_profile("a")
        item = {
            **metadata(data),
            "assignment_id": str(uuid4()),
            "institute_id": str(uuid4()),
            "membership_id": str(uuid4()),
            "study_profile_id": p.cloud_profile_id,
            "institute_name": "Academy",
            "instructions": "Mock test",
        }
        state = {"packs": [item], "data": data}
        with InstituteContentClient(
            "https://cloud.test",
            auth_token="device",
            link_id=link,
            local_profile_id="a",
            transport=transport(state),
        ) as client:
            refresh_work(repo, client, "a", link)
            assert repo.institute_work("b") == []
            assert (
                download_work(
                    repo,
                    client,
                    "a",
                    link,
                    item["assignment_id"],
                    temp_directory=tmp_path,
                    max_pack_bytes=10**6,
                ).status.value
                == "INSTALLED"
            )
            assert repo.visible_question_sets("a") == ()  # not a personal selection
            assert repo.visible_question_sets("b") == ()
            with pytest.raises(ValueError):
                AssessmentApplication(repo).start_test(
                    "b", item["set_id"], 1, institute_assignment_id=item["assignment_id"]
                )
            state["offline"] = True
            with pytest.raises(ContentNetworkError):
                refresh_work(repo, client, "a", link)
            app = AssessmentApplication(repo)
            a = app.start_test(
                "a", item["set_id"], 1, institute_assignment_id=item["assignment_id"]
            )
            app.select_answer("A")
            app.continue_unrated()
            app.pause()
            order = repo.get_attempt_question_order(a.id)
            state["offline"] = False
            completed = AssessmentApplication(repo)
            assert completed.resume_attempt("a").id == a.id
            completed.request_submit()
            completed.submit()
            partial = AssessmentApplication(repo).start_test(
                "a", item["set_id"], 1, institute_assignment_id=item["assignment_id"])
            state["packs"] = []
            refresh_work(repo, client, "a", link)
            assert repo.institute_work("a") == []
            assert repo.get_question_set(item["set_id"], 1) is not None
            resumed = AssessmentApplication(repo)
            assert resumed.resume_attempt("a") is None
            assert repo.get_attempt(partial.id).status.value == "abandoned"
            assert repo.get_attempt_question_order(a.id) == order
            assert repo.get_attempt(a.id).status.value == "completed"
            payload = build_upload_payload(repo, a.id)
            assert payload["institute_assignment_id"] == item["assignment_id"]
            assert payload["ownership"]["study_profile_id"] == p.cloud_profile_id
            assert build_upload_payload(repo, a.id) == payload
            with pytest.raises(ValueError):
                AssessmentApplication(repo).start_test(
                    "a", item["set_id"], 1, institute_assignment_id=item["assignment_id"]
                )
            assert repo.get_attempt_institute_context(a.id)["institute_id"] == item["institute_id"]


def test_institute_ui_profile_scope_and_test_setup(tmp_path):
    data = Path("content/sample_biology.json").read_bytes()
    with Repository(tmp_path / "ui.db") as repo:
        link = setup(repo)
        p = repo.get_profile("a")
        item = {
            **metadata(data),
            "assignment_id": str(uuid4()),
            "institute_id": str(uuid4()),
            "membership_id": str(uuid4()),
            "study_profile_id": p.cloud_profile_id,
            "institute_name": "X",
        }
        repo.cache_institute_work("a", link, [item])
        c = UIController(repo, startup=True)
        c.profile_index = 0
        c.authorized_profile = "a"
        c.route(UIScreen.INSTITUTE_WORK)
        assert any(ch.command == "institute_download" for ch in c.choices)
        c.profile_index = 1
        assert all(ch.command not in {"institute_start", "institute_download"} for ch in c.choices)


def test_wrong_profile_catalogue_cannot_replace_grants(tmp_path):
    with Repository(tmp_path / "pi.db") as repo:
        link = setup(repo)
        with pytest.raises(ValueError, match="owner"):
            repo.cache_institute_work("a", link, [{"study_profile_id": str(uuid4())}])
        assert repo.institute_work("a") == []
