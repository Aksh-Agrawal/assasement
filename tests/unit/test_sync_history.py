import copy
import json
from uuid import uuid4

import httpx
import pytest

from app.content.client import ContentApiClient
from app.core.models import Profile
from app.data.repo import Repository
from app.sync.history import sync_history


def test_paginated_history_atomic_validation_and_transient_recovery(tmp_path):
    account, pid, link, result = (str(uuid4()) for _ in range(4))
    local = "cloud-" + pid
    item = {"attempt_id": result, "study_profile_id": pid, "source": "web", "status": "completed",
        "title": "Browser result", "subject": "Biology", "started_at": "2026-10-30T10:00:00Z",
        "completed_at": "2026-10-30T10:01:00Z", "result": {"score": 4, "maximum_score": 8}}
    broken = [False]
    review_status = 503
    review_calls = []
    calls = []
    def handler(request):
        assert request.headers["Authorization"] == "Bearer device_test.secret"
        if request.url.path.endswith("/history/" + result):
            review_calls.append(review_status)
            if review_status != 200:
                return httpx.Response(review_status)
            return httpx.Response(200, json={**item, "review_available": True,
                "review": [{"question_id": "q1", "question_text": "Question", "is_correct": True}]})
        offset = int(request.url.params["offset"])
        calls.append(offset)
        if offset == 0:
            return httpx.Response(200, json={"items": [item], "next_offset": 1})
        if broken[0]:
            raise httpx.ReadTimeout("timeout", request=request)
        return httpx.Response(200, json={"items": [], "next_offset": None})
    class Api:
        def content(self, *, local_profile_id, link_id):
            return ContentApiClient("https://cloud.test", auth_token="device_test.secret",
                local_profile_id=local_profile_id, link_id=link_id, transport=httpx.MockTransport(handler))
    with Repository(tmp_path / "history.db") as repo:
        repo.create_profile(Profile(local, "Student"))
        repo.apply_profile_link(local, {"status": "linked", "link_id": link, "student_account_id": account,
            "study_profile_id": pid, "local_profile_id": local, "account_display_name": "Student",
            "study_profile_name": "Student"})
        assert not sync_history(repo, Api())
        assert calls == [0, 1]
        saved = repo.completed_results(local)
        assert saved == [item]
        history = json.loads(repo.get_setting("last_history_summary"))
        assert (history["results"], history["failures"], history["review_failures"]) == (1, 0, 1)
        invalid = copy.deepcopy(item)
        invalid["study_profile_id"] = str(uuid4())
        with pytest.raises(ValueError):
            repo.cache_completed_results(local, link, [invalid])
        with pytest.raises(ValueError):
            repo.cache_completed_results(local, link, [item, item])
        assert repo.completed_results(local) == saved
        assert not repo.list_attempts()
        broken[0] = True
        assert not sync_history(repo, Api())
        assert repo.completed_results(local) == saved  # An incomplete page never replaces history.
        broken[0] = False
        review_status = 404  # Older API: summary-only fallback remains successful.
        assert sync_history(repo, Api())
        assert repo.completed_results(local) == saved
        review_status = 200
        assert sync_history(repo, Api())
        assert repo.completed_results(local)[0]["review_available"]
        assert sync_history(repo, Api())
        assert review_calls == [503, 404, 200]
