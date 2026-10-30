"""Automated regression tests for WifiService NetworkManager operations."""

from types import SimpleNamespace

import pytest

from app.system.wifi import (
    WifiAuthenticationError,
    WifiPermissionError,
    WifiService,
    WifiTimeoutError,
)


@pytest.fixture
def wifi_service(monkeypatch):
    monkeypatch.setattr("app.system.wifi.shutil.which", lambda cmd: "/usr/bin/nmcli" if cmd == "nmcli" else None)
    return WifiService()


def test_scan_success_and_deduplication(wifi_service, monkeypatch):
    """Scan deduplicates multiple BSSIDs for the same SSID and marks connected network."""
    raw_output = (
        r"*:HomeHotspot:85:WPA2" + "\n"
        r" :HomeHotspot:60:WPA2" + "\n"  # 2.4 GHz weaker duplicate of above
        r" :Library-Guest:45:--" + "\n"
        r" :School\:\:Special:70:WPA2 WPA3" + "\n"
    )

    def mock_run(cmd, **kwargs):
        return SimpleNamespace(returncode=0, stdout=raw_output, stderr="")

    monkeypatch.setattr("app.system.wifi.subprocess.run", mock_run)
    monkeypatch.setattr(wifi_service, "saved", lambda: ("HomeHotspot",))

    networks = wifi_service.scan()
    assert len(networks) == 3

    by_ssid = {n.ssid: n for n in networks}
    assert "HomeHotspot" in by_ssid
    hotspot = by_ssid["HomeHotspot"]
    assert hotspot.signal_percent == 85
    assert hotspot.connected is True
    assert hotspot.saved is True
    assert hotspot.encrypted is True

    guest = by_ssid["Library-Guest"]
    assert guest.signal_percent == 45
    assert guest.encrypted is False
    assert guest.connected is False

    special = by_ssid["School::Special"]
    assert special.signal_percent == 70
    assert special.encrypted is True


def test_scan_empty(wifi_service, monkeypatch):
    """Scan returning no networks returns empty tuple."""
    monkeypatch.setattr("app.system.wifi.subprocess.run", lambda *a, **kw: SimpleNamespace(returncode=0, stdout="", stderr=""))
    assert wifi_service.scan() == ()


def test_scan_permission_failure_falls_back_without_rescan(wifi_service, monkeypatch):
    """When active rescan triggers permission error, scan falls back to non-rescan listing."""
    calls = []

    def mock_run(cmd, **kwargs):
        calls.append(cmd)
        if "--rescan" in cmd and cmd[cmd.index("--rescan") + 1] == "yes":
            return SimpleNamespace(returncode=4, stdout="", stderr="Error: Scanning not allowed: Not authorized")
        return SimpleNamespace(returncode=0, stdout="*:FallbackWifi:75:WPA2\n", stderr="")

    monkeypatch.setattr("app.system.wifi.subprocess.run", mock_run)
    networks = wifi_service.scan()
    assert len(networks) == 1
    assert networks[0].ssid == "FallbackWifi"
    # Should have attempted rescan yes, fallen back to rescan no, and checked saved connections
    scan_calls = [c for c in calls if "device" in c and "wifi" in c]
    assert len(scan_calls) == 2
    assert "--rescan" in scan_calls[0] and scan_calls[0][scan_calls[0].index("--rescan") + 1] == "yes"
    assert "--rescan" in scan_calls[1] and scan_calls[1][scan_calls[1].index("--rescan") + 1] == "no"


def test_connect_success_with_spaces_and_special_chars(wifi_service, monkeypatch):
    """Connecting with spaces in SSID and symbols in password passes safe argument arrays."""
    recorded = []

    def mock_run(cmd, **kwargs):
        recorded.append(cmd)
        return SimpleNamespace(returncode=0, stdout="Connection successfully activated", stderr="")

    monkeypatch.setattr("app.system.wifi.subprocess.run", mock_run)

    ssid = "Aksh Hotspot 5G"
    password = r"P@$$w0rd!#%^&*()-_+=;:'\",.<>/?`~"

    wifi_service.connect(ssid, password)
    assert len(recorded) == 1
    cmd = recorded[0]
    assert cmd[0] == "nmcli"
    assert cmd[1] == "--wait"
    assert cmd[2] == "25"
    assert cmd[3:6] == ["device", "wifi", "connect"]
    assert cmd[6] == ssid
    assert cmd[7] == "password"
    assert cmd[8] == password


def test_connect_wrong_password_raises_authentication_error(wifi_service, monkeypatch):
    """Wrong password error output raises WifiAuthenticationError."""
    def mock_run(cmd, **kwargs):
        return SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="Error: Connection activation failed: Secrets were required, but not provided.",
        )

    monkeypatch.setattr("app.system.wifi.subprocess.run", mock_run)

    with pytest.raises(WifiAuthenticationError, match="Check your password"):
        wifi_service.connect("TestNet", "wrong_password")


def test_connect_authorization_failure_raises_permission_error(wifi_service, monkeypatch):
    """Polkit authorization denial raises WifiPermissionError."""
    def mock_run(cmd, **kwargs):
        return SimpleNamespace(
            returncode=4,
            stdout="",
            stderr="Error: Connection activation failed: Not authorized to control networking.",
        )

    monkeypatch.setattr("app.system.wifi.subprocess.run", mock_run)

    with pytest.raises(WifiPermissionError, match="authorization failed"):
        wifi_service.connect("TestNet", "pass")


def test_connect_timeout_raises_timeout_error(wifi_service, monkeypatch):
    """Connection timeout raises WifiTimeoutError."""
    def mock_run(cmd, **kwargs):
        return SimpleNamespace(
            returncode=2,
            stdout="",
            stderr="Error: Connection activation failed: Activation timed out.",
        )

    monkeypatch.setattr("app.system.wifi.subprocess.run", mock_run)

    with pytest.raises(WifiTimeoutError, match="timed out"):
        wifi_service.connect("WeakNet", "pass")


def test_connect_saved_network(wifi_service, monkeypatch):
    """Connecting to an already saved network without password uses connection up."""
    recorded = []

    def mock_run(cmd, **kwargs):
        recorded.append(cmd)
        return SimpleNamespace(returncode=0, stdout="Connection successfully activated", stderr="")

    monkeypatch.setattr("app.system.wifi.subprocess.run", mock_run)
    monkeypatch.setattr(wifi_service, "saved", lambda: ("SavedHome",))

    wifi_service.connect("SavedHome", "", saved=True)
    assert len(recorded) == 1
    assert recorded[0][-4:] == ["connection", "up", "id", "SavedHome"]


def test_forget_network(wifi_service, monkeypatch):
    """Forgetting a network deletes the NM connection profile."""
    recorded = []

    def mock_run(cmd, **kwargs):
        recorded.append(cmd)
        return SimpleNamespace(returncode=0, stdout="Connection 'OldNet' successfully deleted.", stderr="")

    monkeypatch.setattr("app.system.wifi.subprocess.run", mock_run)

    wifi_service.forget("OldNet")
    assert recorded[0][-4:] == ["connection", "delete", "id", "OldNet"]


def test_connected_ssid_detection(wifi_service, monkeypatch):
    """Detects active SSID from device status output."""
    raw_status = (
        "eth0:ethernet:unavailable:--\n"
        "wlan0:wifi:connected:AkshPhoneHotspot\n"
        "lo:loopback:unmanaged:--\n"
    )

    def mock_run(cmd, **kwargs):
        return SimpleNamespace(returncode=0, stdout=raw_status, stderr="")

    monkeypatch.setattr("app.system.wifi.subprocess.run", mock_run)

    assert wifi_service.connected_ssid() == "AkshPhoneHotspot"
    assert wifi_service.connected() is True
