"""Privileged, fixed-purpose systemd updater for the Raspberry Pi appliance.

This file is installed outside the versioned application tree. The UI can only
request a version; paths, trust roots, commands, and service names are fixed.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

APP_ROOT = Path(os.environ.get("ASSESS_APP_ROOT", "/opt/questraa-device")).resolve()
DATA_ROOT = Path(os.environ.get("ASSESS_DATA_DIR", "/var/lib/assessdev")).resolve()
UPDATE_ROOT = Path(os.environ.get("ASSESS_UPDATE_DIR", str(DATA_ROOT / "update"))).resolve()
INBOX = Path(os.environ.get("ASSESS_UPDATE_INBOX", str(UPDATE_ROOT / "inbox"))).resolve()
REQUEST = INBOX / "request.json"
STATUS = UPDATE_ROOT / "status.json"
TRANSACTION = UPDATE_ROOT / "transaction.json"
UI_UNIT = os.environ.get("ASSESS_UI_UNIT", "assessdev-ui.service")
SERVICE_USER = os.environ.get("ASSESS_SERVICE_USER", "aksh")
VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
MAX_SIGNED_ARTIFACT_BYTES = 1_000_000_000
MAX_MANIFEST_BYTES = 64 * 1024


def _systemctl(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["/usr/bin/systemctl", *args], check=check, capture_output=True, text=True)


def _status(state: str, version: str, detail: str = "") -> None:
    UPDATE_ROOT.mkdir(parents=True, exist_ok=True)
    tmp = STATUS.with_suffix(".tmp")
    tmp.write_text(json.dumps({"state": state, "version": version, "detail": detail}), encoding="utf-8")
    os.chmod(tmp, 0o644)
    tmp.replace(STATUS)


def _copy_untrusted_regular_file(source: Path, destination: Path, maximum: int) -> int:
    """Copy a user-owned updater file into a root-only directory without links."""
    metadata = source.lstat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > maximum:
        raise RuntimeError("Update staging contains a non-regular or oversized file")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    source_fd = os.open(source, flags)
    destination_fd = -1
    try:
        opened = os.fstat(source_fd)
        if (
            not stat.S_ISREG(opened.st_mode)
            or (opened.st_dev, opened.st_ino) != (metadata.st_dev, metadata.st_ino)
            or opened.st_size > maximum
        ):
            raise RuntimeError("Update staging file changed during verification")
        destination_fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        copied = 0
        while chunk := os.read(source_fd, 1024 * 1024):
            copied += len(chunk)
            if copied > maximum:
                raise RuntimeError("Update staging file exceeds its size limit")
            view = memoryview(chunk)
            while view:
                written = os.write(destination_fd, view)
                view = view[written:]
        os.fsync(destination_fd)
        return copied
    finally:
        os.close(source_fd)
        if destination_fd >= 0:
            os.close(destination_fd)


def _activation_metadata(current: str | None, previous: str | None, state: str) -> None:
    path = UPDATE_ROOT / "current_release.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({
        "current": current, "previous": previous, "staged": None, "status": state,
    }, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def recover_interrupted_install() -> int:
    """Run before the kiosk at boot to finish or reverse a power-cut update."""
    if os.geteuid() != 0:
        raise SystemExit("Recovery must run as root")
    status = json.loads(STATUS.read_text(encoding="utf-8")) if STATUS.exists() else {}
    transaction = json.loads(TRANSACTION.read_text(encoding="utf-8")) if TRANSACTION.exists() else None
    if status.get("state") != "installing":
        return 0
    if not transaction:
        status_version = str(status.get("version", ""))
        selected_version = json.loads(
            ((APP_ROOT / "current").resolve(strict=True) / "release.json").read_text(encoding="utf-8")
        )["version"]
        if selected_version == status_version:
            raise RuntimeError("Active release has no update transaction record")
        _status("failed", status_version, "Power was interrupted before release activation")
        return 0
    version = transaction["version"]
    old_version = transaction["previous"]
    current = APP_ROOT / "current"
    selected = current.resolve(strict=True)
    selected_version = json.loads((selected / "release.json").read_text(encoding="utf-8"))["version"]
    if selected_version == old_version:
        _status("failed", version, "Power was interrupted before activation")
        _activation_metadata(old_version, None, "healthy")
        TRANSACTION.unlink(missing_ok=True)
        return 0
    if selected_version != version:
        raise RuntimeError("Interrupted update points to an unexpected release")
    python = selected / ".venv" / "bin/python"
    smoke = subprocess.run(
        [str(python), "-m", "app.ui_qt.main", "--db", str(UPDATE_ROOT / "recovery-smoke.db"), "--smoke-test"],
        cwd=selected, env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True, text=True, timeout=90,
    )
    if smoke.returncode == 0:
        (UPDATE_ROOT / "recovery-smoke.db").unlink(missing_ok=True)
        _install_stable_helper(selected)
        _status("successful", version, "Recovered after an unexpected restart")
        _activation_metadata(version, old_version, "healthy")
        TRANSACTION.unlink(missing_ok=True)
        return 0
    backup_value = transaction.get("database_backup")
    database = Path(os.environ.get("ASSESS_SQLITE_PATH", str(DATA_ROOT / "assessment-device.db")))
    credential_path = Path(os.environ.get("ASSESS_CREDENTIAL_PATH", str(DATA_ROOT / "device_credentials.json")))
    _restore_data_backup(database, Path(backup_value) if backup_value else None, credential_path)
    previous = APP_ROOT / "releases" / old_version
    rollback = APP_ROOT / "current.recovery"
    rollback.unlink(missing_ok=True)
    rollback.symlink_to(previous)
    rollback.replace(current)
    _status("rolled_back", version, "Recovered the previous application after an unexpected restart")
    _activation_metadata(old_version, version, "rolled_back")
    TRANSACTION.unlink(missing_ok=True)
    return 0


def _backup_database(
    database: Path,
    backup_root: Path | None = None,
    credential_path: Path | None = None,
) -> Path | None:
    if not database.exists():
        return None
    backup_dir = (backup_root or DATA_ROOT / "backups") / time.strftime("%Y%m%d-%H%M%S")
    backup_dir.mkdir(parents=True, exist_ok=False)
    backup_db = backup_dir / database.name
    source = sqlite3.connect(database)
    target = sqlite3.connect(backup_db)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    credentials = credential_path or DATA_ROOT / "device_credentials.json"
    if credentials.exists():
        shutil.copy2(credentials, backup_dir / credentials.name)
    return backup_db


def _restore_data_backup(database: Path, backup_db: Path | None, credential_path: Path) -> None:
    """Restore only missing files; never replace state written after backup.

    Replacing a live SQLite file with the pre-activation snapshot can discard
    completed attempts and pending sync rows created while the new UI starts.
    Application rollback therefore keeps live data and uses backups only when
    a file is missing.
    """
    if not backup_db or not backup_db.exists():
        return
    database.parent.mkdir(parents=True, exist_ok=True)
    if not database.exists():
        shutil.copy2(backup_db, database)
    backup_credentials = backup_db.parent / credential_path.name
    if backup_credentials.exists() and not credential_path.exists():
        credential_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = credential_path.with_suffix(credential_path.suffix + ".restore")
        shutil.copy2(backup_credentials, temporary)
        temporary.replace(credential_path)


def _run_migration_probe(python: Path, database: Path, *, expected_success: bool) -> bool:
    code = (
        "from app.data.repo import Repository; "
        f"r=Repository({str(database)!r}); "
        "assert r.schema_version >= 1; "
        "assert r.integrity_check().ok; r.close()"
    )
    result = subprocess.run(
        [str(python), "-c", code], capture_output=True, text=True, timeout=120,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    return (result.returncode == 0) is expected_success


def _protected_data_snapshot(database: Path) -> dict[str, list[tuple]]:
    if not database.exists():
        return {}
    protected = {
        "profiles": "id, display_name, pin_hash, pin_salt, created_at, deleted_at, cloud_account_id, cloud_profile_id, ownership_state, link_state",
        "question_sets": "id, version, title, content_hash, is_active",
        "questions": "set_id, set_version, id, position, question_text, correct_key",
        "attempts": "id, profile_id, set_id, set_version, status, started_at, completed_at, duration_ms, score, sync_status, sync_attempts, last_sync_error, synced_at, next_sync_at, sync_started_at, sync_error_kind",
        "attempt_questions": "attempt_id, position, question_id",
        "responses": "id, attempt_id, question_id, selected_key, confidence, is_correct, response_time_ms, first_shown_at, answered_at, marked_review",
        "response_events": "id, attempt_id, question_id, event_type, value, at_ms, at_utc",
        "settings": "key, value",
        "private_pack_versions": "set_id, version",
        "profile_link_context": "local_profile_id, link_id, account_display_name, study_profile_name",
        "attempt_ownership": "attempt_id, study_profile_id, link_id",
        "student_account_context": "singleton, cloud_account_id, display_name, auth_state, last_verified_at, offline_policy",
        "profile_library": "local_profile_id, set_id, version, link_id, metadata_json, eligible",
        "institute_work": "local_profile_id, assignment_id, link_id, metadata_json, eligible",
        "attempt_institute_context": "attempt_id, assignment_id, institute_id, membership_id, study_profile_id",
    }
    result: dict[str, list[tuple]] = {}
    with sqlite3.connect(database) as connection:
        present = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table, columns in protected.items():
            if table in present:
                result[table] = connection.execute(f"SELECT {columns} FROM {table} ORDER BY 1").fetchall()
    return result


def _install_stable_helper(release: Path) -> None:
    source = release / "tools" / "updater_service.py"
    if not source.is_file():
        return
    destination = Path("/usr/local/libexec/assessdev-updater.py")
    temporary = destination.with_suffix(".next")
    shutil.copyfile(source, temporary)
    os.chmod(temporary, 0o755)
    os.chown(temporary, 0, 0)
    temporary.replace(destination)


def _healthy(version: str, previous_pid: str) -> bool:
    deadline = time.monotonic() + 35
    first_pid = ""
    while time.monotonic() < deadline:
        state = subprocess.run(
            ["/usr/bin/systemctl", "show", UI_UNIT, "--property=ActiveState", "--value"],
            capture_output=True, text=True, check=False,
        ).stdout.strip()
        pid = subprocess.run(
            ["/usr/bin/systemctl", "show", UI_UNIT, "--property=MainPID", "--value"],
            capture_output=True, text=True, check=False,
        ).stdout.strip()
        if state != "active" or not pid or pid == "0":
            time.sleep(1)
            continue
        if not first_pid:
            first_pid = pid
        if pid != first_pid:
            return False
        time.sleep(15)
        state2 = subprocess.run(
            ["/usr/bin/systemctl", "show", UI_UNIT, "--property=ActiveState", "--value"],
            capture_output=True, text=True, check=False,
        ).stdout.strip()
        pid2 = subprocess.run(
            ["/usr/bin/systemctl", "show", UI_UNIT, "--property=MainPID", "--value"],
            capture_output=True, text=True, check=False,
        ).stdout.strip()
        return state2 == "active" and pid2 == first_pid and pid2 != previous_pid
    return False


def main() -> int:
    import grp
    import pwd
    if sys.argv[1:] == ["--recover"]:
        return recover_interrupted_install()
    if os.geteuid() != 0:
        raise SystemExit("The updater must run as root through its fixed systemd unit")
    current_link = APP_ROOT / "current"
    old_release = current_link.resolve(strict=True)
    old_version = json.loads((old_release / "release.json").read_text(encoding="utf-8"))["version"]
    request_stat = REQUEST.lstat()
    assess_uid = pwd.getpwnam(SERVICE_USER).pw_uid
    service_group = os.environ.get("ASSESS_SERVICE_GROUP", SERVICE_USER)
    assess_gid = grp.getgrnam(service_group).gr_gid
    if not REQUEST.is_file() or REQUEST.is_symlink() or request_stat.st_uid != assess_uid:
        raise RuntimeError("Update request is not a regular file owned by the device account")
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    version = str(request.get("version", ""))
    if not VERSION_RE.fullmatch(version) or version == old_version:
        raise RuntimeError("Update request version is invalid")

    # Load the release verification implementation from the currently active,
    # immutable release. The trusted public key and target are root configured.
    sys.path.insert(0, str(old_release))
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    from app.config import AppConfig
    from app.data.repo import Repository
    from app.update.layout import configured_installation_paths, validate_trusted_app_root
    from app.update.staging import stage_update
    from app.update.verifier import verify_update

    configured = configured_installation_paths(os.environ)
    account = pwd.getpwnam(SERVICE_USER)
    validate_trusted_app_root(
        configured.app_root,
        account.pw_uid,
        set(os.getgrouplist(SERVICE_USER, account.pw_gid)),
    )
    config = AppConfig()
    if config.database_path.resolve() != configured.database_path:
        raise RuntimeError("Configured SQLite path does not match the validated updater data path")
    if config.credential_path.resolve() != configured.credential_path:
        raise RuntimeError("Configured credential path does not match the validated updater data path")
    _status("installing", version)
    staged_user = UPDATE_ROOT / "staged" / version
    manifest_path = staged_user / "update-manifest.json"
    signature_path = staged_user / "update-manifest.sig"
    staged_metadata = staged_user.lstat()
    if not stat.S_ISDIR(staged_metadata.st_mode) or staged_metadata.st_uid != assess_uid:
        raise RuntimeError("Staged release directory is not a device-owned directory")
    manifest_info = manifest_path.lstat()
    if not stat.S_ISREG(manifest_info.st_mode) or manifest_info.st_size > MAX_MANIFEST_BYTES:
        raise RuntimeError("Staged update manifest is not a regular bounded file")
    # Extract and build dependencies before stopping the assessment UI. This
    # cannot affect the running release or its data if download/install fails.
    work = Path(tempfile.mkdtemp(prefix="questraa-update-", dir=APP_ROOT))
    try:
        manifest_copy = work / "update-manifest.json"
        signature_copy = work / "update-manifest.sig"
        if _copy_untrusted_regular_file(manifest_path, manifest_copy, MAX_MANIFEST_BYTES) != manifest_info.st_size:
            raise RuntimeError("Update manifest changed while being copied")
        # Parse only the root-owned copy; staged metadata is user-writable.
        manifest_hint = json.loads(manifest_copy.read_text(encoding="utf-8"))
        filename = manifest_hint.get("artifact", {}).get("filename", "")
        declared_size = manifest_hint.get("artifact", {}).get("size_bytes", 0)
        if (
            not isinstance(filename, str) or Path(filename).name != filename
            or manifest_hint.get("release", {}).get("version") != version
            or not isinstance(declared_size, int) or not 0 < declared_size <= MAX_SIGNED_ARTIFACT_BYTES
        ):
            raise RuntimeError("Update release metadata is invalid")
        source_artifact = UPDATE_ROOT / "downloads" / filename
        artifact_info = source_artifact.lstat()
        if not stat.S_ISREG(artifact_info.st_mode) or artifact_info.st_size != declared_size:
            raise RuntimeError("Downloaded update artifact is missing, linked or truncated")
        required = declared_size * 4 + 300_000_000
        if shutil.disk_usage(APP_ROOT).free < required:
            raise RuntimeError("There is not enough free storage to safely install the update")
        artifact = work / filename
        if _copy_untrusted_regular_file(signature_path, signature_copy, 64) != 64:
            raise RuntimeError("Update signature has an invalid size")
        if _copy_untrusted_regular_file(source_artifact, artifact, MAX_SIGNED_ARTIFACT_BYTES) != declared_size:
            raise RuntimeError("Update artifact changed while being copied")
        manifest_bytes = manifest_copy.read_bytes()
        with Repository(config.database_path) as repository:
            database_schema = repository.schema_version
        key = load_pem_public_key(config.trusted_update_public_key_path.read_bytes())
        verified = verify_update(
            manifest_bytes, signature_copy.read_bytes(), artifact,
            trusted_keys={config.trusted_update_key_id: key},
            current_version=old_version, platform=config.update_platform,
            architecture=config.update_architecture, db_schema=database_schema,
        )
        staged = stage_update(verified, work)
        new_venv = staged / ".venv"
        subprocess.run(["/usr/bin/python3", "-m", "venv", str(new_venv)], check=True, timeout=180)
        subprocess.run(
            [str(new_venv / "bin/python"), "-m", "pip", "install", "--disable-pip-version-check",
             "--no-cache-dir", "--retries", "2", ".[gui]"],
            cwd=staged, check=True, timeout=1200,
        )
        probe_db = work / "migration-probe.db"
        if config.database_path.exists():
            with sqlite3.connect(config.database_path) as source, sqlite3.connect(probe_db) as target:
                source.backup(target)
        protected_before = _protected_data_snapshot(probe_db)
        if not _run_migration_probe(new_venv / "bin/python", probe_db, expected_success=True):
            raise RuntimeError("The update could not safely migrate a test copy of local data")
        if _protected_data_snapshot(probe_db) != protected_before:
            raise RuntimeError("The migration changed or removed saved student assessment data")
        # Rollback must still read the new, forward-migrated schema.
        smoke_db = work / "ui-smoke.db"
        smoke = subprocess.run(
            [str(new_venv / "bin/python"), "-m", "app.ui_qt.main", "--db", str(smoke_db), "--smoke-test"],
            cwd=staged, env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True, text=True, timeout=90,
        )
        if smoke.returncode:
            raise RuntimeError("The update failed the Qt startup check")

        release_dir = APP_ROOT / "releases" / version
        if release_dir.exists():
            raise RuntimeError("That release version is already installed")
        release_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staged), str(release_dir))
        shutil.chown(release_dir, user="root", group=service_group)
        for directory, _subdirs, files in os.walk(release_dir):
            os.chown(directory, 0, assess_gid)
            for name in files:
                os.chown(Path(directory) / name, 0, assess_gid)

        old_pid = subprocess.run(
            ["/usr/bin/systemctl", "show", UI_UNIT, "--property=MainPID", "--value"],
            capture_output=True, text=True, check=False,
        ).stdout.strip()
        _systemctl("stop", UI_UNIT)
        backup = _backup_database(config.database_path, credential_path=config.credential_path)
        transaction_tmp = TRANSACTION.with_suffix(".tmp")
        transaction_tmp.write_text(json.dumps({
            "version": version, "previous": old_version,
            "database_backup": str(backup) if backup else None,
        }), encoding="utf-8")
        transaction_tmp.replace(TRANSACTION)
        next_link = APP_ROOT / "current.next"
        next_link.unlink(missing_ok=True)
        next_link.symlink_to(release_dir)
        next_link.replace(current_link)
        _activation_metadata(version, old_version, "activating")
        _systemctl("start", UI_UNIT)
        if _healthy(version, old_pid):
            _install_stable_helper(release_dir)
            _status("successful", version)
            _activation_metadata(version, old_version, "healthy")
            TRANSACTION.unlink(missing_ok=True)
            REQUEST.unlink(missing_ok=True)
            return 0

        _systemctl("stop", UI_UNIT, check=False)
        _restore_data_backup(config.database_path, backup, config.credential_path)
        previous_link = APP_ROOT / "current.rollback"
        previous_link.unlink(missing_ok=True)
        previous_link.symlink_to(old_release)
        previous_link.replace(current_link)
        _activation_metadata(old_version, version, "rolled_back")
        _systemctl("start", UI_UNIT, check=False)
        _status("rolled_back", version, f"Restored application {old_version}; local data backup: {backup or 'not needed'}")
        TRANSACTION.unlink(missing_ok=True)
        REQUEST.unlink(missing_ok=True)
        return 0
    finally:
        if work.exists():
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        UPDATE_ROOT.mkdir(parents=True, exist_ok=True)
        _status("failed", "", type(error).__name__)
        REQUEST.unlink(missing_ok=True)
        raise
