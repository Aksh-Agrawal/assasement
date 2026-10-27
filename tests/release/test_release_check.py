"""Focused regression tests for the Phase 10F release runner."""

import json
from pathlib import Path

import pytest

from tools.release_check import (
    CheckResult,
    ReleaseCheck,
    Status,
    _pytest_counts,
    _test_db_safety,
)


def test_pytest_counts_are_machine_readable() -> None:
    assert _pytest_counts("7 passed, 2 skipped, 4 deselected in 1.2s") == {
        "passed": 7,
        "skipped": 2,
        "deselected": 4,
    }


def test_required_failure_controls_overall_and_reports_are_redacted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = "postgresql://user:super-secret@localhost/assessment_test"
    monkeypatch.setenv("TEST_DATABASE_URL", secret)
    runner = ReleaseCheck(mode="offline", report_directory=tmp_path)
    runner.add(
        "Example",
        CheckResult("required", Status.FAIL, 0.1, secret, required=True),
    )
    report = runner._build_report()
    runner._write_reports(report)
    assert report.overall_status is Status.FAIL
    assert secret not in (tmp_path / "release-readiness.json").read_text(encoding="utf-8")


def test_reports_have_stable_status_values(tmp_path: Path) -> None:
    runner = ReleaseCheck(mode="offline", report_directory=tmp_path)
    runner.skip("Backend", "Network", "offline mode")
    report = runner._build_report()
    runner._write_reports(report)
    payload = json.loads((tmp_path / "release-readiness.json").read_text(encoding="utf-8"))
    assert payload["overall_status"] == "PASS"
    assert payload["groups"][0]["checks"][0]["status"] == "SKIP"
    assert payload["hardware_status"] == "PENDING"


def test_test_database_safety_rejects_non_test_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql://localhost/assessment_prod")
    with pytest.raises(RuntimeError, match="named with 'test'"):
        _test_db_safety()
