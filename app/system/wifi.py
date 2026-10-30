"""Bounded NetworkManager adapter. UI values are arguments, never shell code."""

import logging
import shutil
import subprocess
from dataclasses import dataclass

LOGGER = logging.getLogger(__name__)


class WifiError(RuntimeError):
    """Base error for Wi-Fi operations."""


class WifiPermissionError(WifiError):
    """NetworkManager authorization failure (polkit required)."""


class WifiAuthenticationError(WifiError):
    """Wi-Fi authentication failure (bad password or secrets required)."""


class WifiNotFoundError(WifiError):
    """Target wireless network not found or out of range."""


class WifiTimeoutError(WifiError):
    """NetworkManager connection activation timed out."""


@dataclass(frozen=True)
class WifiNetwork:
    ssid: str
    signal: str
    security: str
    saved: bool = False
    connected: bool = False

    @property
    def signal_percent(self) -> int:
        try:
            return max(0, min(100, int(self.signal)))
        except (ValueError, TypeError):
            return 70

    @property
    def encrypted(self) -> bool:
        sec = (self.security or "").strip().lower()
        return bool(sec and sec != "--" and sec != "none")


class WifiService:
    @property
    def available(self) -> bool:
        return shutil.which("nmcli") is not None

    def _run(self, *arguments, wait: int = 10, timeout: int = 15) -> str:
        if not self.available:
            raise WifiError("Wi-Fi controls unavailable on this platform")

        cmd = ["nmcli", "--wait", str(wait), *arguments]
        # Never log raw command arguments that might include Wi-Fi passwords
        safe_args = [
            "[REDACTED_PASSWORD]" if i > 0 and cmd[i - 1] == "password" else arg
            for i, arg in enumerate(cmd)
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            LOGGER.warning("nmcli subprocess timed out command=%s", safe_args)
            raise WifiTimeoutError(
                "Wi-Fi operation timed out. Network may be weak or busy."
            ) from exc

        if result.returncode:
            err = (result.stderr or result.stdout or "").strip()
            err_lower = err.lower()
            LOGGER.warning(
                "nmcli failed returncode=%d cmd=%s error=%s",
                result.returncode,
                safe_args,
                err,
            )
            if any(p in err_lower for p in ["not authorized", "insufficient privileges", "polkit", "permission denied"]):
                raise WifiPermissionError(
                    "NetworkManager authorization failed. Device user lacks permission."
                )
            if any(p in err_lower for p in ["secrets were required", "bad password", "pre-shared key", "psk", "invalid key", "secret"]):
                raise WifiAuthenticationError(
                    "Connection failed. Check your password and try again."
                )
            if any(p in err_lower for p in ["no network with ssid", "not found", "could not find"]):
                raise WifiNotFoundError(
                    "Network not found. It may be out of range or powered off."
                )
            if any(p in err_lower for p in ["timeout", "timed out", "did not respond"]):
                raise WifiTimeoutError(
                    "Wi-Fi connection timed out. Check signal and try again."
                )
            raise WifiError(
                err or "Wi-Fi action failed. Check network and permissions, then retry."
            )

        return result.stdout

    @staticmethod
    def _fields(line: str) -> list[str]:
        fields, current, escaped = [], "", False
        for char in line:
            if escaped:
                current += char
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == ":":
                fields.append(current)
                current = ""
            else:
                current += char
        return fields + [current]

    def scan(self) -> tuple[WifiNetwork, ...]:
        """Scan for available Wi-Fi networks, deduplicating multiple BSSIDs per SSID."""
        if not self.available:
            return ()

        # Try active rescan first; fall back to cached list if polkit or driver forbids active rescan
        try:
            rows = self._run(
                "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "device", "wifi", "list", "--rescan", "yes"
            )
        except (WifiPermissionError, WifiError):
            try:
                rows = self._run(
                    "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "device", "wifi", "list", "--rescan", "no"
                )
            except Exception as exc:
                LOGGER.warning("Wi-Fi scan failed completely: %s", exc)
                return ()

        saved_set = set(self.saved())
        networks_by_ssid: dict[str, WifiNetwork] = {}

        for row in rows.splitlines():
            if not row:
                continue
            fields = self._fields(row)
            if len(fields) < 4:
                # Handle backwards compatibility with older 3-field format
                if len(fields) == 3:
                    in_use, ssid, signal, security = "", fields[0], fields[1], fields[2]
                else:
                    continue
            else:
                in_use, ssid, signal, security = fields[0], fields[1], fields[2], fields[3]

            ssid = ssid.strip()
            if not ssid:
                continue

            try:
                sig_val = int(signal)
            except (ValueError, TypeError):
                sig_val = 50

            is_connected = in_use.strip() == "*"
            is_saved = ssid in saved_set

            existing = networks_by_ssid.get(ssid)
            if existing is None or is_connected or sig_val > existing.signal_percent:
                networks_by_ssid[ssid] = WifiNetwork(
                    ssid=ssid,
                    signal=str(sig_val),
                    security=security,
                    saved=is_saved,
                    connected=is_connected or (existing.connected if existing else False),
                )

        return tuple(networks_by_ssid.values())

    def saved(self) -> tuple[str, ...]:
        if not self.available:
            return ()
        try:
            rows = self._run("-t", "-f", "NAME,TYPE", "connection", "show")
        except Exception as exc:
            LOGGER.warning("nmcli connection show failed: %s", exc)
            return ()
        return tuple(
            self._fields(r)[0]
            for r in rows.splitlines()
            if r and self._fields(r)[-1] in {"802-11-wireless", "wifi"}
        )

    def connected_ssid(self) -> str | None:
        """Return the SSID of the currently active Wi-Fi connection, or None."""
        if not self.available:
            return None
        try:
            rows = self._run("-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device", "status")
            for row in rows.splitlines():
                if not row:
                    continue
                fields = self._fields(row)
                if len(fields) >= 4 and fields[1] in {"wifi", "802-11-wireless"} and fields[2] == "connected":
                    conn = fields[3].strip()
                    if conn and conn != "--":
                        return conn
        except Exception as exc:
            LOGGER.warning("nmcli device status check failed: %s", exc)

        # Fallback: check device wifi list for IN-USE marker
        try:
            wifi_rows = self._run("-t", "-f", "IN-USE,SSID", "device", "wifi", "list", wait=5, timeout=8)
            for row in wifi_rows.splitlines():
                fields = self._fields(row)
                if len(fields) >= 2 and fields[0].strip() == "*":
                    active_ssid = fields[1].strip()
                    if active_ssid:
                        return active_ssid
        except Exception:
            pass

        return None

    def connect(self, ssid: str, password: str = "", *, saved: bool = False) -> None:
        """Connect to wireless network. Sufficient timeout allowed for Pi Zero 2 W DHCP."""
        if saved or (not password and ssid in self.saved()):
            self._run("connection", "up", "id", ssid, wait=25, timeout=30)
        else:
            args = ["device", "wifi", "connect", ssid]
            if password:
                args += ["password", password]
            self._run(*args, wait=25, timeout=30)

    def forget(self, name: str) -> None:
        self._run("connection", "delete", "id", name)

    def connected(self) -> bool:
        if not self.available:
            return False
        return self.connected_ssid() is not None

    def internet_status(self) -> str:
        """NetworkManager's independent connectivity observation, without a new probe."""
        if not self.available:
            return "Unknown"
        try:
            value = self._run("-t", "-f", "CONNECTIVITY", "general", "status", wait=5, timeout=8).strip().lower()
        except Exception:
            return "Unknown"
        return {
            "full": "Available",
            "limited": "Limited",
            "portal": "Sign-in required",
            "none": "Offline",
            "unknown": "Unknown",
        }.get(value, "Unknown")
