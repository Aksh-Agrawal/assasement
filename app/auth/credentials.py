"""Replaceable local storage for the one-time-issued device credential."""

import getpass
import json
import os
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DeviceCredential:
    device_id: str
    token: str = field(repr=False)


class CredentialStore:
    """Atomic JSON credential store; production Pi storage can replace this class."""

    def __init__(self, path: Path = Path("var/device_credentials.json")) -> None:
        self.path = path

    def save(self, credential: DeviceCredential) -> None:
        if any(not isinstance(value, str) or not value.strip()
               for value in (credential.device_id, credential.token)):
            raise ValueError("Invalid device credential")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(prefix=".credential-", dir=self.path.parent)
        temporary = Path(name)
        try:
            # mkstemp creates mode 0600 from the start, before any token is written.
            self._restrict(temporary)
            with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                descriptor = -1
                json.dump(asdict(credential), output)
                output.flush()
                os.fsync(output.fileno())
            temporary.replace(self.path)
            if os.name != "nt":
                directory = os.open(self.path.parent, os.O_RDONLY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
        finally:
            if descriptor != -1:
                os.close(descriptor)
            temporary.unlink(missing_ok=True)

    def load(self) -> DeviceCredential | None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        if (not isinstance(data, dict) or set(data) != {"device_id", "token"}
                or any(not isinstance(data[k], str) or not data[k].strip()
                       for k in ("device_id", "token"))):
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
