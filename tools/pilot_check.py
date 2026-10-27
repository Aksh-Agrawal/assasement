"""Run offline-first pilot readiness checks with optional backend verification."""

import argparse
import tempfile
from pathlib import Path
from types import SimpleNamespace

from app.assessment import AssessmentApplication
from app.config import AppConfig
from app.content.importer import import_pack
from app.core.models import Profile
from app.data.repo import Repository
from app.diagnostics import HealthLevel
from tools.diagnose import collect


def smoke_assessment() -> bool:
    with tempfile.TemporaryDirectory(prefix="assessment-smoke-") as name:
        with Repository(Path(name) / "smoke.db") as repository:
            import_pack(Path("content/sample_biology.json"), repository)
            profile = repository.create_profile(Profile("smoke-profile", "Smoke Test"))
            app = AssessmentApplication(repository)
            app.start_test(profile.id, "biology-cell-practice-01", 1)
            app.select_answer("A")
            app.continue_unrated()
            app.request_submit()
            result = app.submit()
            return result.correct + result.wrong + result.skipped == 20


def main() -> int:
    config = AppConfig()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=config.database_path)
    parser.add_argument("--credentials", type=Path, default=Path("var/device_credentials.json"))
    parser.add_argument("--base-url", default=config.api_base_url)
    parser.add_argument("--update-root", type=Path, default=config.update_root)
    parser.add_argument("--trusted-key-id", default=config.trusted_update_key_id)
    parser.add_argument(
        "--trusted-public-key",
        type=Path,
        default=config.trusted_update_public_key_path,
    )
    parser.add_argument("--network", action="store_true")
    parser.add_argument("--skip-smoke", action="store_true")
    args = parser.parse_args()
    status = collect(
        SimpleNamespace(
            **vars(args),
            connect_timeout=config.sync_connect_timeout,
            read_timeout=config.sync_read_timeout,
            json=False,
        )
    )
    checks: list[tuple[str, str]] = []
    checks.append(("PASS" if status.get("local_db_status") == "ok" else "FAIL", "Local DB"))
    checks.append(("PASS" if status.get("schema_version") else "FAIL", "Schema"))
    checks.append(("PASS" if status.get("device_id_present") else "FAIL", "Device identity"))
    checks.append(("PASS" if status.get("installed_content_count", 0) else "FAIL", "Content available"))
    checks.append(("PASS" if status.get("paired") else "WARN", "Pairing state"))
    checks.append(
        (
            "PASS" if args.trusted_public_key.is_file() else "WARN",
            "Update verifier configured",
        )
    )
    checks.append(("PASS", "Sync queue readable") if "completed_pending_sync" in status else ("FAIL", "Sync queue readable"))
    if args.skip_smoke:
        checks.append(("WARN", "Assessment smoke test skipped"))
    else:
        checks.append(("PASS" if smoke_assessment() else "FAIL", "Assessment smoke test"))
    if status.get("staged_release"):
        checks.append(("WARN", "Staged update pending"))
    else:
        checks.append(("PASS", "No pending destructive state"))
    network = status.get("network", {})
    if args.network:
        checks.append(("PASS" if network.get("backend_reachable") else "WARN", "Backend reachable"))
        checks.append(("PASS" if network.get("database_ready") else "WARN", "Backend database ready"))
    checks.append(
        (
            "PASS" if status.get("offline_assessment_ready") else "FAIL",
            "Offline assessment readiness",
        )
    )
    for level, label in checks:
        print(f"{level:<5} {label}")
    if any(level == "FAIL" for level, _label in checks) or status["health"] == HealthLevel.ERROR.value:
        return 2
    if any(level == "WARN" for level, _label in checks) or status["health"] != HealthLevel.OK.value:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
