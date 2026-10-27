"""Read-only Raspberry Pi OS, resource, temperature, and throttle diagnostic."""

import argparse
import os
import platform
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Metric:
    name: str
    status: str
    value: str


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace").rstrip("\x00\n")
    except OSError:
        return None


def _command(*command: str) -> tuple[str, str]:
    executable = shutil.which(command[0])
    if executable is None:
        return "UNAVAILABLE", f"{command[0]} not found"
    try:
        result = subprocess.run(
            (executable, *command[1:]),
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return "UNAVAILABLE", str(error)
    output = (result.stdout or result.stderr).strip()
    if result.returncode != 0:
        return "UNAVAILABLE", output or f"exit status {result.returncode}"
    return "AVAILABLE", output


def _memory() -> str:
    text = _read_text(Path("/proc/meminfo"))
    if text is None:
        return "platform API unavailable"
    values: dict[str, str] = {}
    for line in text.splitlines():
        key, _, value = line.partition(":")
        if key in {"MemTotal", "MemAvailable"}:
            values[key] = value.strip()
    return ", ".join(f"{key}={value}" for key, value in values.items())


def _load() -> str:
    try:
        one, five, fifteen = os.getloadavg()
    except (AttributeError, OSError):
        return "load average unavailable"
    return f"1m={one:.2f}, 5m={five:.2f}, 15m={fifteen:.2f}, CPUs={os.cpu_count()}"


def _disk() -> str:
    usage = shutil.disk_usage(Path.cwd().anchor or "/")
    gib = 1024**3
    return (
        f"total={usage.total / gib:.1f} GiB, used={usage.used / gib:.1f} GiB, "
        f"free={usage.free / gib:.1f} GiB"
    )


def collect_metrics() -> tuple[Metric, ...]:
    model = _read_text(Path("/proc/device-tree/model"))
    is_pi = model is not None and "Raspberry Pi" in model
    pi_status = "AVAILABLE" if is_pi else "NOT RUNNING ON RASPBERRY PI"
    os_release = _read_text(Path("/etc/os-release"))
    temp_status, temperature = _command("vcgencmd", "measure_temp")
    throttle_status, throttling = _command("vcgencmd", "get_throttled")
    return (
        Metric("Raspberry Pi", pi_status, model or "model device-tree entry unavailable"),
        Metric("OS", "AVAILABLE", os_release or platform.platform()),
        Metric("Kernel", "AVAILABLE", platform.release()),
        Metric("Architecture", "AVAILABLE", platform.machine()),
        Metric("RAM", "AVAILABLE", _memory()),
        Metric("CPU/load", "AVAILABLE", _load()),
        Metric("Temperature", temp_status, temperature),
        Metric("Throttling", throttle_status, throttling),
        Metric("Disk", "AVAILABLE", _disk()),
    )


def print_report() -> None:
    print(f"Timestamp UTC: {datetime.now(UTC).isoformat(timespec='seconds')}")
    for metric in collect_metrics():
        print(f"{metric.name}: {metric.status}\n  {metric.value}")


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watch", action="store_true", help="repeat temperature/throttle report")
    parser.add_argument("--interval", type=float, default=5.0, help="watch interval in seconds")
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    if args.interval <= 0:
        print("--interval must be positive")
        return 2
    try:
        while True:
            print_report()
            if not args.watch:
                return 0
            print()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
