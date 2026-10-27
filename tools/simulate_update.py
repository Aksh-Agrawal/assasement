"""Verify, stage, activate, health-check, and if necessary roll back locally."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from app.update.activation import ActivationManager
from app.update.staging import stage_update
from tools.verify_release import add_arguments, verify_files


def _health(path: Path) -> bool:
    environment = {**os.environ, "PYTHONPATH": str(path)}
    result = subprocess.run(
        [sys.executable, "-m", "app.main", "--health-check"],
        cwd=path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    parser.add_argument("--update-root", type=Path, default=Path("runtime/updates"))
    parser.add_argument("--current-release", type=Path)
    args = parser.parse_args()
    root = args.update_root
    verified = verify_files(args)
    staged = stage_update(verified, root)
    manager = ActivationManager(root)
    if manager.metadata()["current"] is None:
        if args.current_release is None:
            raise SystemExit("--current-release is required when activation metadata is empty")
        manager.initialize(args.current_version, args.current_release)
    healthy = manager.activate(staged, str(verified.manifest.version), _health)
    print("Activation healthy." if healthy else "Activation failed; previous release restored.")
    return 0 if healthy else 1


if __name__ == "__main__":
    raise SystemExit(main())
