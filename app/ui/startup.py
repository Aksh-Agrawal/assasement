"""Incremental, local-only startup checks. Each yielded row follows real work."""

from dataclasses import dataclass
from pathlib import Path

from app.auth.credentials import CredentialStore
from app.config import AppConfig
from app.data.repo import Repository
from app.update.activation import ActivationManager


@dataclass(frozen=True)
class StartupCheck:
    label: str
    detail: str
    ok: bool = True


class StartupSession:
    def __init__(self, path: Path, config: AppConfig, credentials: CredentialStore):
        self.path, self.config, self.credentials = path, config, credentials
        self.repository = None
        self.rows: list[StartupCheck] = []
        self.failed = False
        self.complete = False
        self.steps = self._checks()

    def _checks(self):
        yield StartupCheck("Configuration", f"Software {self.config.application_version}")
        self.repository = Repository(self.path)
        yield StartupCheck("Local database", "Opened; integrity validated")
        yield StartupCheck(
            "Schema / migrations", f"Current schema {self.repository.schema_version}"
        )
        identity = self.repository.get_or_create_device_id()
        yield StartupCheck("Device identity", identity[:8])
        yield StartupCheck(
            "Credentials",
            "Paired" if self.credentials.load_safe() else "Not paired; local use available",
        )
        packs = self.repository.list_question_sets()
        yield StartupCheck("Question content", f"{len(packs)} installed versions")
        count = sum(
            self.repository.find_in_progress_attempt(p.id) is not None
            for p in self.repository.list_profiles()
        )
        yield StartupCheck("Interrupted assessments", f"{count} available to resume")
        try:
            state = ActivationManager(self.config.update_root).metadata().get("status", "idle")
            yield StartupCheck("Update state", str(state))
        except (OSError, ValueError):
            yield StartupCheck("Update state", "Needs attention; current app remains usable", False)
        if not self.repository.quick_check().ok:
            raise RuntimeError("Local diagnostic check failed")
        yield StartupCheck("Local diagnostics", "Ready")

    def advance(self):
        if self.complete or self.failed:
            return
        try:
            self.rows.append(next(self.steps))
        except StopIteration:
            self.complete = True
        except Exception:
            self.failed = True
            self.rows.append(
                StartupCheck("Local startup", "Unable to open safely. Support code DB-001", False)
            )

    def close(self):
        if self.repository is not None:
            self.repository.close()
