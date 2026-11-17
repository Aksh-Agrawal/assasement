from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.assessment import AssessmentApplication
from app.core.models import Confidence
from app.data.intelligence import load_intelligence
from app.data.repo import Repository
from tests.integration.test_assessment import PROFILE, seed


def test_offline_snapshot_keeps_native_evidence_and_scopes_checks(tmp_path):
    database = tmp_path / "learning.db"
    account, profile, link, web = (str(uuid4()) for _ in range(4))
    with Repository(database) as repo:
        content = seed(repo)
        app = AssessmentApplication(repo, wall_clock=lambda: datetime(2026, 1, 2, tzinfo=UTC))
        attempt = app.start_test(PROFILE.id, content.id, 1, question_count=2)
        app.select_answer("B")
        app.set_confidence(Confidence.SURE)
        app.request_submit()
        app.submit()
        repo.apply_profile_link(PROFILE.id, {
            "status": "linked", "link_id": link, "student_account_id": account,
            "study_profile_id": profile, "local_profile_id": PROFILE.id,
            "account_display_name": "Learner", "study_profile_name": "Learner",
        })
        summary = {
            "attempt_id": web, "study_profile_id": profile, "source": "web", "status": "completed",
            "title": "Web practice", "started_at": "2026-01-02T23:58:00Z",
            "completed_at": "2026-01-03T00:01:00Z", "subject": "Biology",
            "chapter": "Development Fixtures", "set_id": content.id, "version": 1,
            "marking": {"correct": 4, "wrong": -1, "skip": 0},
            "result": {"score": 4, "maximum_score": 4, "correct": 1, "wrong": 0, "skipped": 0},
            "review_available": True, "review_evidence_version": 1,
            "review": [{"question_id": "new-q", "response_id": str(uuid4()), "topic": "Phase 4",
                        "question_type": "multiple_choice", "difficulty": 3,
                        "selected_key": "B", "confidence": "not_sure", "is_correct": True}],
        }
        duplicate = {**summary, "attempt_id": attempt.id, "source": "device", "title": "Old summary",
                     "completed_at": "2026-01-02T00:00:00Z", "started_at": "2026-01-02T00:00:00Z"}
        for _ in range(2):
            repo.cache_completed_results(PROFILE.id, link, [summary, duplicate])
        checks = {"schema_version": 1, "study_profile_id": profile, "recovery": [],
                  "retention": [{"id": "topic", "topic": "Phase 4", "status": "upcoming",
                                 "day": 3, "due_at": "2026-01-05T00:00:00Z", "history": []}]}
        with pytest.raises(ValueError):
            repo.cache_analytics_checks(PROFILE.id, str(uuid4()), checks)
        for _ in range(2):
            repo.cache_analytics_checks(PROFILE.id, link, checks)

    view = load_intelligence(database, PROFILE.id, 5)
    assert view["metrics"]["attempts"] == 2
    assert view["metrics"]["skipped"] == 1
    assert view["knowledge"]["overall"]["quadrants"] == {
        "confident_correct": 0, "confident_wrong": 1, "uncertain_correct": 1, "uncertain_wrong": 0,
    }
    assert view["knowledge"]["topics"][0]["evidence"][0]["attempt_id"] == attempt.id
    assert view["checks_cached"] and len(view["retention"]) == 1
    assert view["strategy"]["modelled_questions"] == 0
    assert load_intelligence(database, "another-profile", 5) == {}

    with Repository(database) as repo:
        repo.retire_profile_link(PROFILE.id, reason="test_revocation")
    offline = load_intelligence(database, PROFILE.id, 20)
    assert offline["metrics"]["attempts"] == 1 and not offline["checks_cached"]
    assert offline["knowledge"]["overall"]["quadrants"]["confident_wrong"] == 1
