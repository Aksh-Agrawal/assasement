"""Cross-platform versioned activation metadata with simulated health rollback."""

import json
import logging
import shutil
from collections.abc import Callable
from pathlib import Path

from app.update.errors import StagingError

HealthCheck = Callable[[Path], bool]
LOGGER = logging.getLogger(__name__)


class ActivationManager:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.releases = root / "releases"
        self.metadata_path = root / "current_release.json"

    def metadata(self) -> dict:
        if not self.metadata_path.exists():
            return {"current": None, "previous": None, "staged": None, "status": "idle"}
        return json.loads(self.metadata_path.read_text(encoding="utf-8"))

    def initialize(self, version: str, release_path: Path) -> None:
        self.releases.mkdir(parents=True, exist_ok=True)
        target = self.releases / version
        if not target.exists():
            shutil.copytree(release_path, target)
        self._write({"current": version, "previous": None, "staged": None, "status": "healthy"})

    def activate(self, staged: Path, version: str, health_check: HealthCheck) -> bool:
        LOGGER.info("update activation started: version=%s", version)
        self.releases.mkdir(parents=True, exist_ok=True)
        before = self.metadata()
        target = self.releases / version
        if target.exists():
            raise StagingError("Release directory already exists")
        staged.replace(target)
        self._write({"current": version, "previous": before["current"], "staged": version, "status": "activating"})
        if health_check(target):
            self._write({"current": version, "previous": before["current"], "staged": None, "status": "healthy"})
            LOGGER.info("update activation succeeded: version=%s", version)
            return True
        self._write({"current": before["current"], "previous": version, "staged": None, "status": "rolled_back"})
        LOGGER.warning(
            "update activation failed; rolled back: failed_version=%s current=%s",
            version,
            before["current"],
        )
        return False

    def _write(self, data: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = self.metadata_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
        temporary.replace(self.metadata_path)
