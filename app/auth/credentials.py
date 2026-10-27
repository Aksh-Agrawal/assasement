"""Replaceable local storage for the one-time-issued device credential."""

import getpass
import json
import os
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DeviceCredential:
    device_id: str
    token: str


class CredentialStore:
    """Atomic JSON credential store; production Pi storage can replace this class."""

    def __init__(self, path: Path = Path("var/device_credentials.json")) -> None:
        self.path = path

    def save(self, credential: DeviceCredential) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(asdict(credential)), encoding="utf-8")
        os.chmod(temporary, 0o600)
        temporary.replace(self.path)
        self._restrict(self.path)

    def load(self) -> DeviceCredential | None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        if set(data) != {"device_id", "token"}:
            raise ValueError("Invalid device credential file")
        return DeviceCredential(device_id=str(data["device_id"]), token=str(data["token"]))

    def load_safe(self) -> DeviceCredential | None:
        """Treat missing, unreadable, or malformed development storage as unpaired."""
        try:
            return self.load()
        except (OSError, ValueError):
            return None

    def clear(self) -> None:
        self.path.unlink(missing_ok=True)

    @staticmethod
    def _restrict(path: Path) -> None:
        os.chmod(path, 0o600)
        if os.name == "nt":
            try:
                subprocess.run(
                    [
                        "icacls",
                        str(path),
                        "/inheritance:r",
                        "/grant:r",
                        f"{getpass.getuser()}:(R,W)",
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except (OSError, subprocess.CalledProcessError):
                # NTFS ACL hardening is best-effort for portable development storage.
                pass
