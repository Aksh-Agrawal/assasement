"""Read system power information without requiring a battery on the Pi."""

from pathlib import Path


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="ascii").strip()
    except (OSError, UnicodeError):
        return ""


def battery_label(root: Path = Path("/sys/class/power_supply")) -> str:
    try:
        supplies = sorted(root.iterdir())
    except OSError:
        supplies = ()
    plugged_in = False
    for supply in supplies:
        supply_type = _read(supply / "type")
        if supply_type != "Battery":
            plugged_in |= bool(supply_type and _read(supply / "online") == "1")
            continue
        if _read(supply / "scope") == "Device" or _read(supply / "present") == "0":
            continue
        capacity = _read(supply / "capacity")
        if capacity.isdecimal() and 0 <= int(capacity) <= 100:
            return f"{int(capacity)}%"
    return "Cable power" if plugged_in else "Battery unavailable"
