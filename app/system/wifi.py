"""Bounded NetworkManager adapter. UI values are arguments, never shell code."""

import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class WifiNetwork:
    ssid: str
    signal: str
    security: str
    saved: bool = False


class WifiService:
    @property
    def available(self):
        return shutil.which("nmcli") is not None

    def _run(self, *arguments):
        if not self.available:
            raise RuntimeError("Wi-Fi controls unavailable on this platform")
        result = subprocess.run(
            ["nmcli", "--wait", "10", *arguments],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if result.returncode:
            raise RuntimeError("Wi-Fi action failed. Check network and permissions, then retry.")
        return result.stdout

    @staticmethod
    def _fields(line):
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

    def scan(self):
        rows = self._run(
            "-t", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list", "--rescan", "yes"
        )
        return tuple(
            WifiNetwork(*self._fields(row)[:3])
            for row in rows.splitlines()
            if row and self._fields(row)[0]
        )

    def saved(self):
        rows = self._run("-t", "-f", "NAME,TYPE", "connection", "show")
        return tuple(
            self._fields(r)[0]
            for r in rows.splitlines()
            if self._fields(r)[-1] == "802-11-wireless"
        )

    def connect(self, ssid, password="", *, saved=False):
        if saved:
            self._run("connection", "up", "id", ssid)
        else:
            args = ["device", "wifi", "connect", ssid]
            if password:
                args += ["password", password]
            self._run(*args)

    def forget(self, name):
        self._run("connection", "delete", "id", name)

    def connected(self):
        if not self.available:
            return False
        rows = self._run("-t", "-f", "TYPE,STATE", "device", "status")
        return any(self._fields(row)[:2] == ["wifi", "connected"] for row in rows.splitlines())
