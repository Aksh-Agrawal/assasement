"""One-command laptop software release-readiness validation.

Default mode is offline and never probes a backend or PostgreSQL. Full mode uses
the existing integration suites and requires an explicitly named PostgreSQL test
database. Exit codes: 0 PASS, 1 PASS with warnings, 2 FAIL.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
import zipfile
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from app import __version__
from app.auth.credentials import CredentialStore, DeviceCredential
from app.content.importer import import_pack
from app.content.validator import PackValidationError, validate_pack
from app.data.db import check_integrity, connect_database, run_migrations
from app.data.repo import Repository
from app.diagnostics import redact_text
from tools.create_support_bundle import create_support_bundle
from tools.pilot_check import smoke_assessment

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIRECTORY = ROOT / "artifacts"
PYTEST_SUMMARY = re.compile(
    r"(?P<count>\d+) (?P<kind>passed|failed|skipped|deselected|error|errors)"
)


class Status(StrEnum):
    """Stable result states emitted to terminal and reports."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass(slots=True)
class CheckResult:
    name: str
    status: Status
    duration: float
    message: str
    error_code: str | None = None
    required: bool = True
    tests: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class CheckGroupResult:
    name: str
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def status(self) -> Status:
        if any(item.status is Status.FAIL and item.required for item in self.checks):
            return Status.FAIL
        if any(item.status is Status.WARN for item in self.checks):
            return Status.WARN
        if self.checks and all(item.status is Status.SKIP for item in self.checks):
            return Status.SKIP
        return Status.PASS


@dataclass(slots=True)
class ReleaseReport:
    timestamp: str
    app_version: str
    backend_version: str
    mode: str
    overall_status: Status
    duration: float
    environment: dict[str, str]
    counts: dict[str, int]
    test_totals: dict[str, int]
    hardware_status: str
    groups: list[CheckGroupResult]


class ReleaseCheck:
    def __init__(self, *, mode: str, report_directory: Path) -> None:
        self.mode = mode
        self.report_directory = report_directory
        self.groups: dict[str, CheckGroupResult] = {}
        self.started = time.monotonic()
        self.secrets = tuple(
            value
            for value in (
                os.environ.get("DATABASE_URL"),
                os.environ.get("TEST_DATABASE_URL"),
            )
            if value
        )

    def add(self, group: str, result: CheckResult) -> CheckResult:
        self.groups.setdefault(group, CheckGroupResult(group)).checks.append(result)
        print(f"{result.status.value:<5} {result.name} - {result.message}")
        return result

    def check(
        self,
        group: str,
        name: str,
        operation: Callable[[], str | None],
        *,
        required: bool = True,
        error_code: str | None = None,
    ) -> CheckResult:
        started = time.monotonic()
        try:
            message = operation() or "check completed"
            result = CheckResult(name, Status.PASS, time.monotonic() - started, message)
        except Exception as error:
            message = redact_text(str(error), secrets=self.secrets)
            result = CheckResult(
                name,
                Status.FAIL if required else Status.WARN,
                time.monotonic() - started,
                message or error.__class__.__name__,
                error_code,
                required,
            )
        return self.add(group, result)

    def skip(self, group: str, name: str, message: str) -> None:
        self.add(group, CheckResult(name, Status.SKIP, 0.0, message, required=False))

    def command(
        self,
        group: str,
        name: str,
        arguments: list[str],
        *,
        required: bool = True,
        accepted_codes: tuple[int, ...] = (0,),
        validate: Callable[[subprocess.CompletedProcess[str]], str] | None = None,
        error_code: str | None = None,
    ) -> CheckResult:
        started = time.monotonic()
        completed = subprocess.run(
            arguments,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        duration = time.monotonic() - started
        combined = redact_text(
            "\n".join(part for part in (completed.stdout, completed.stderr) if part),
            secrets=self.secrets,
        )
        tests = _pytest_counts(combined)
        try:
            if completed.returncode not in accepted_codes:
                tail = " | ".join(line.strip() for line in combined.splitlines()[-4:] if line.strip())
                raise RuntimeError(
                    f"exit {completed.returncode}" + (f": {tail}" if tail else "")
                )
            message = validate(completed) if validate else _command_summary(combined, tests)
            if "pytest" in arguments and tests.get("passed", 0) == 0:
                raise RuntimeError("required pytest selection executed no passing tests")
            result = CheckResult(name, Status.PASS, duration, message, tests=tests)
        except Exception as error:
            result = CheckResult(
                name,
                Status.FAIL if required else Status.WARN,
                duration,
                redact_text(str(error), secrets=self.secrets),
                error_code,
                required,
                tests,
            )
        return self.add(group, result)

    def pytest(self, group: str, name: str, *selection: str) -> CheckResult:
        return self.command(
            group,
            name,
            [sys.executable, "-m", "pytest", "-q", "--tb=short", *selection],
            error_code="TEST_FAILED",
        )

    def run(self) -> ReleaseReport:
        self._preflight()
        self.command(
            "Code quality",
            "Ruff",
            [sys.executable, "-m", "ruff", "check", "."],
            error_code="RUFF_FAILED",
        )
        self._offline_checks()
        if self.mode == "full":
            self._full_checks()
        else:
            self._offline_skips()
        report = self._build_report()
        self._write_reports(report)
        print(f"\nOverall: {report.overall_status.value}")
        print(f"JSON report: {self.report_directory / 'release-readiness.json'}")
        print(f"Markdown report: {self.report_directory / 'release-readiness.md'}")
        return report

    def _preflight(self) -> None:
        self.check("Pre-flight", "Python version", _python_version)
        self.check("Pre-flight", "Required files", _required_files)
        self.check("Pre-flight", "Version consistency", _version_consistency)

    def _offline_checks(self) -> None:
        self.pytest("Device core", "Device unit suite", "tests/unit")
        self.pytest(
            "Device core",
            "Assessment smoke",
            "tests/integration/test_assessment.py::test_full_twenty_question_assessment_uses_repository_and_phase2_scoring",
        )
        self.pytest(
            "Device core",
            "Resume after restart",
            "tests/integration/test_assessment.py::test_crash_restart_resume_restores_order_answers_flags_confidence_and_time",
        )
        self.pytest("Device core", "Device UI integration", "tests/integration/test_ui_integration.py")
        self.check("Device core", "Isolated pilot smoke", _assessment_smoke)

        self.check("Persistence", "Fresh SQLite migration/integrity/WAL", _sqlite_check)
        self.pytest(
            "Persistence",
            "Persistence regression suite",
            "tests/integration/test_database.py",
            "tests/integration/test_repository.py",
        )

        self.check("Content", "Known-good and invalid pack validation", _pack_validation)
        self.pytest(
            "Content",
            "Content and version-pinning suite",
            "tests/integration/test_pack_import.py",
            "tests/content",
        )
        self.pytest("Sync", "Offline sync retention suite", "tests/integration/test_sync.py")
        self.pytest(
            "Updates",
            "Signed update, compatibility, and tamper suite",
            "tests/update/test_updates.py",
            "-k",
            "not authenticated_update_check_and_download_limit and not update_check_auth_failure",
        )
        self.check("Updates", "Private signing-key safety", _private_key_safety)
        self.pytest("Recovery", "Deterministic fault/recovery suite", "tests/faults")
        self.pytest("Observability", "Observability regression suite", "tests/observability")
        self._diagnostics_commands()

    def _diagnostics_commands(self) -> None:
        with tempfile.TemporaryDirectory(prefix="release-observability-") as name:
            root = Path(name)
            database = root / "device.db"
            credentials = root / "credentials.json"
            update_root = root / "updates"
            public_key = root / "trusted-public.pem"
            with Repository(database) as repository:
                import_pack(ROOT / "content/sample_biology.json", repository)
                device_id = repository.get_or_create_device_id()
            CredentialStore(credentials).save(
                DeviceCredential(device_id, "device_releasecheck.redaction-canary")
            )
            public_key.write_bytes(
                Ed25519PrivateKey.generate()
                .public_key()
                .public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
            )

            def validate_json(completed: subprocess.CompletedProcess[str]) -> str:
                parsed = json.loads(completed.stdout)
                serialized = json.dumps(parsed)
                if "redaction-canary" in serialized or "DATABASE_URL" in serialized:
                    raise RuntimeError("diagnostic JSON contains secret-bearing data")
                return f"valid JSON; health={parsed.get('health')}"

            self.command(
                "Observability",
                "diagnose --json",
                [
                    sys.executable,
                    "-m",
                    "tools.diagnose",
                    "--json",
                    "--db",
                    str(database),
                    "--credentials",
                    str(credentials),
                    "--update-root",
                    str(update_root),
                ],
                validate=validate_json,
            )
            self.check(
                "Observability",
                "Support bundle redaction",
                lambda: _support_bundle_check(root, database, credentials, update_root),
            )
            self.command(
                "Pilot readiness",
                "pilot_check",
                [
                    sys.executable,
                    "-m",
                    "tools.pilot_check",
                    "--db",
                    str(database),
                    "--credentials",
                    str(credentials),
                    "--update-root",
                    str(update_root),
                    "--trusted-public-key",
                    str(public_key),
                ],
            )

    def _offline_skips(self) -> None:
        message = "offline mode does not require FastAPI, PostgreSQL, or network"
        for group, name in (
            ("Backend", "FastAPI integration"),
            ("PostgreSQL", "PostgreSQL connection/migration head"),
            ("Authentication", "Pairing and authenticated requests"),
            ("Sync", "Real PostgreSQL attempt sync/lost acknowledgement"),
            ("Content", "Remote catalog/download v1-to-v2"),
            ("Updates", "Authenticated update API"),
            ("Pilot readiness", "Full software-only pilot simulation"),
        ):
            self.skip(group, name, message)

    def _full_checks(self) -> None:
        environment = self.check("PostgreSQL", "Database configuration", _database_config)
        safety = self.check("PostgreSQL", "Designated test DB safety", _test_db_safety)
        if environment.status is Status.FAIL or safety.status is Status.FAIL:
            self.add(
                "PostgreSQL",
                CheckResult(
                    "PostgreSQL destructive integration",
                    Status.FAIL,
                    0.0,
                    "not run because database pre-flight failed",
                    "POSTGRES_PREFLIGHT_FAILED",
                ),
            )
            self.skip("Pilot readiness", "Full software-only pilot simulation", "database pre-flight failed")
            return

        self.pytest(
            "Backend",
            "FastAPI health and migrations",
            "backend/tests/test_health.py",
            "backend/tests/test_migrations.py",
        )
        self.pytest("Authentication", "Pairing and revocation", "backend/tests/test_pairing.py")
        self.pytest(
            "Authentication",
            "Protected endpoint and invalid credential",
            "backend/tests/test_attempt_upload.py::test_authentication_required_and_invalid_token_rejected",
        )
        self.pytest(
            "Sync",
            "Backend upload, idempotency, and lost-ack",
            "backend/tests/test_attempt_upload.py",
            "backend/tests/test_idempotency.py",
            "backend/tests/test_end_to_end.py",
        )
        self.pytest(
            "Content",
            "Authenticated catalog/download/import v1-to-v2",
            "backend/tests/test_content.py",
            "backend/tests/test_content_end_to_end.py",
        )
        self.pytest("Updates", "Authenticated update API", "backend/tests/test_updates.py")
        self.pytest(
            "PostgreSQL",
            "PostgreSQL connection, migration, rollback",
            "backend/tests/test_postgresql.py::test_postgres_migration_schema_and_constraints",
            "backend/tests/test_postgresql.py::test_postgres_response_failure_rolls_back_entire_attempt",
        )
        self.check("PostgreSQL", "Alembic migration head", _alembic_head)
        self.pytest(
            "Pilot readiness",
            "Full software-only pilot simulation",
            "backend/tests/test_postgresql.py::test_real_device_sync_idempotency_restart_and_failure_recovery",
            "backend/tests/test_postgresql.py::test_real_postgres_content_flow_preserves_active_attempt",
        )

    def _build_report(self) -> ReleaseReport:
        groups = list(self.groups.values())
        checks = [item for group in groups for item in group.checks]
        required_failure = any(item.required and item.status is Status.FAIL for item in checks)
        warning = any(item.status is Status.WARN for item in checks)
        overall = Status.FAIL if required_failure else Status.WARN if warning else Status.PASS
        counts = {status.value: sum(item.status is status for item in checks) for status in Status}
        test_totals: dict[str, int] = {}
        for item in checks:
            for key, value in item.tests.items():
                test_totals[key] = test_totals.get(key, 0) + value
        return ReleaseReport(
            timestamp=datetime.now(UTC).isoformat(),
            app_version=__version__,
            backend_version=_backend_version(),
            mode=self.mode,
            overall_status=overall,
            duration=time.monotonic() - self.started,
            environment={
                "python": platform.python_version(),
                "implementation": platform.python_implementation(),
                "os": platform.system(),
                "os_release": platform.release(),
            },
            counts=counts,
            test_totals=test_totals,
            hardware_status="PENDING",
            groups=groups,
        )

    def _write_reports(self, report: ReleaseReport) -> None:
        self.report_directory.mkdir(parents=True, exist_ok=True)
        payload = _jsonable(asdict(report))
        serialized = redact_text(json.dumps(payload, indent=2), secrets=self.secrets)
        (self.report_directory / "release-readiness.json").write_text(
            serialized + "\n", encoding="utf-8"
        )
        lines = [
            "# Release readiness",
            "",
            f"- Timestamp: {report.timestamp}",
            f"- Mode: {report.mode}",
            f"- Application version: {report.app_version}",
            f"- Overall: **{report.overall_status.value}**",
            f"- Duration: {report.duration:.2f}s",
            "- Software checks: complete when all required checks pass",
            "- Raspberry Pi hardware validation: **PENDING**",
            "",
            "| Area | Check | Status | Evidence |",
            "|---|---|---:|---|",
        ]
        for group in report.groups:
            for item in group.checks:
                message = item.message.replace("|", "\\|").replace("\n", " ")
                lines.append(f"| {group.name} | {item.name} | {item.status.value} | {message} |")
        lines.extend(
            [
                "",
                "## Hardware work still pending",
                "",
                "Phase 6B Pi hardware verification, Phase 7B Pi GUI benchmark, Phase 8B Pi UI "
                "validation, physical GPIO, Pi networking/credentials/content download, real Pi "
                "update activation/reboot, boot-to-app/systemd, and power/thermal validation.",
                "",
            ]
        )
        markdown = redact_text("\n".join(lines), secrets=self.secrets)
        (self.report_directory / "release-readiness.md").write_text(markdown, encoding="utf-8")


def _python_version() -> str:
    configured = ">=3.11"
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r"(?m)^requires-python\s*=\s*\"([^\"]+)\"", pyproject)
    if match:
        configured = match.group(1)
    current = Version(platform.python_version())
    if current not in SpecifierSet(configured):
        raise RuntimeError(f"Python {current} does not satisfy {configured}")
    return f"Python {current} satisfies {configured}"


def _required_files() -> str:
    required = (
        "schemas/pack.schema.json",
        "schemas/update_manifest.schema.json",
        "docs/API.md",
        "docs/ARCHITECTURE.md",
        "content/sample_biology.json",
    )
    missing = [value for value in required if not (ROOT / value).is_file()]
    if missing:
        raise RuntimeError("missing required files: " + ", ".join(missing))
    return f"{len(required)} required files present"


def _version_consistency() -> str:
    canonical = Version(__version__)
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    if 'version = {attr = "app.version.__version__"}' not in pyproject:
        raise RuntimeError("pyproject does not use the canonical app version")
    return f"canonical version {canonical} is parseable and package-linked"


def _backend_version() -> str:
    text = (ROOT / "backend/pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r"(?m)^version\s*=\s*\"([^\"]+)\"", text)
    return match.group(1) if match else "unknown"


def _assessment_smoke() -> str:
    if not smoke_assessment():
        raise RuntimeError("isolated assessment smoke returned false")
    return "temporary profile/pack/attempt submitted, scored, and reviewed"


def _sqlite_check() -> str:
    with tempfile.TemporaryDirectory(prefix="release-sqlite-") as name:
        path = Path(name) / "fresh.db"
        connection = connect_database(path)
        try:
            version = run_migrations(connection)
            integrity = check_integrity(connection)
            journal_mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0]).lower()
        finally:
            connection.close()
        if not integrity.ok:
            raise RuntimeError("SQLite integrity_check did not return ok")
        if journal_mode != "wal":
            raise RuntimeError(f"SQLite journal mode is {journal_mode}, expected wal")
        return f"schema={version}; integrity=ok; journal_mode=wal"


def _pack_validation() -> str:
    good = validate_pack(ROOT / "tests/fixtures/packs/valid_20_questions.json")
    try:
        validate_pack(ROOT / "tests/fixtures/packs/duplicate_question_id.json")
    except PackValidationError:
        pass
    else:
        raise RuntimeError("known-invalid duplicate-question pack was accepted")
    return f"good pack {good.summary.set_id}:v{good.summary.version}; invalid fixture rejected"


def _private_key_safety() -> str:
    excluded = {".venv", ".git", "var", "dist", "artifacts", "__pycache__", ".pytest_cache"}
    private_files: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or excluded.intersection(path.relative_to(ROOT).parts):
            continue
        if path.name.endswith(".update-private.pem"):
            private_files.append(path.relative_to(ROOT).as_posix())
            continue
        if path.stat().st_size <= 1_000_000:
            raw = path.read_bytes()
            if re.search(
                rb"-----BEGIN [^-]*PRIVATE KEY-----\r?\n"
                rb"[A-Za-z0-9+/=\r\n]{32,}-----END [^-]*PRIVATE KEY-----",
                raw,
            ):
                private_files.append(path.relative_to(ROOT).as_posix())
    if private_files:
        raise RuntimeError("private signing key material found in source tree: " + ", ".join(private_files))
    note = "source-tree scan passed"
    if not (ROOT / ".git").exists():
        note += "; .git metadata unavailable, so tracked-file enumeration was not possible"
    return note


def _support_bundle_check(
    root: Path, database: Path, credentials: Path, update_root: Path
) -> str:
    logs = root / "logs"
    logs.mkdir()
    (logs / "assessment-device.log").write_text(
        "Authorization: Bearer device_releasecheck.redaction-canary\n"
        "TEST_DATABASE_URL=postgresql://user:password@localhost/test\n",
        encoding="utf-8",
    )
    bundle = create_support_bundle(
        database_path=database,
        credential_path=credentials,
        log_directory=logs,
        update_root=update_root,
        output_directory=root / "support",
        trusted_key_id="release-check",
    )
    with zipfile.ZipFile(bundle) as archive:
        names = set(archive.namelist())
        content = b"\n".join(archive.read(name) for name in names)
    forbidden_names = {database.name, credentials.name}
    if names.intersection(forbidden_names):
        raise RuntimeError("support bundle contains database or credential file")
    for needle in (b"redaction-canary", b"user:password", b"BEGIN PRIVATE KEY"):
        if needle in content:
            raise RuntimeError("support bundle contains secret-bearing content")
    return f"{len(names)} redacted entries; no database, credentials, answers, or key"


def _database_config() -> str:
    missing = [name for name in ("DATABASE_URL", "TEST_DATABASE_URL") if not os.environ.get(name)]
    if missing:
        raise RuntimeError(
            "missing " + ", ".join(missing) + "; configure both without placing values in logs"
        )
    return "DATABASE_URL and TEST_DATABASE_URL are set (values redacted)"


def _test_db_safety() -> str:
    from sqlalchemy.engine import make_url

    value = os.environ.get("TEST_DATABASE_URL")
    if not value:
        raise RuntimeError("TEST_DATABASE_URL is missing")
    parsed = make_url(value)
    if not parsed.drivername.startswith("postgresql"):
        raise RuntimeError("TEST_DATABASE_URL must use PostgreSQL")
    if not parsed.database or "test" not in parsed.database.lower():
        raise RuntimeError("refusing destructive checks outside a database named with 'test'")
    return "PostgreSQL URL targets an explicitly named test database"


def _alembic_head() -> str:
    from alembic.config import Config
    from alembic.migration import MigrationContext
    from alembic.script import ScriptDirectory
    from sqlalchemy import create_engine
    from sqlalchemy.engine import make_url

    value = os.environ["TEST_DATABASE_URL"]
    parsed = make_url(value)
    if not parsed.database or "test" not in parsed.database.lower():
        raise RuntimeError("test database safety check failed")
    config = Config(str(ROOT / "backend/alembic.ini"))
    script = ScriptDirectory.from_config(config)
    expected = script.get_current_head()
    engine = create_engine(value)
    try:
        with engine.connect() as connection:
            current = MigrationContext.configure(connection).get_current_revision()
    finally:
        engine.dispose()
    if current != expected:
        raise RuntimeError("test database is not at the expected Alembic head")
    return f"database revision matches head {expected}"


def _pytest_counts(output: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for match in PYTEST_SUMMARY.finditer(output):
        kind = match.group("kind")
        if kind == "errors":
            kind = "error"
        counts[kind] = max(counts.get(kind, 0), int(match.group("count")))
    return counts


def _command_summary(output: str, tests: dict[str, int]) -> str:
    if tests:
        return ", ".join(f"{value} {key}" for key, value in sorted(tests.items()))
    for line in reversed(output.splitlines()):
        if line.strip():
            return line.strip()[:300]
    return "command completed successfully"


def _jsonable(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    mode = result.add_mutually_exclusive_group()
    mode.add_argument("--offline", action="store_true", help="safe default; no backend/network")
    mode.add_argument("--full", action="store_true", help="run backend and real PostgreSQL suites")
    result.add_argument("--report-directory", type=Path, default=DEFAULT_REPORT_DIRECTORY)
    return result


def main() -> int:
    args = parser().parse_args()
    mode = "full" if args.full else "offline"
    report = ReleaseCheck(mode=mode, report_directory=args.report_directory).run()
    if report.overall_status is Status.FAIL:
        return 2
    if report.overall_status is Status.WARN:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
