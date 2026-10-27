"""Minimal project status entry point."""

import argparse

from app import __version__

DEVELOPMENT_MESSAGE = "Assessment Device - Phase 10C signed-update architecture"


def main() -> int:
    """Run the development skeleton without initializing external services."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--health-check", action="store_true")
    args = parser.parse_args()
    if args.health_check:
        print(f"healthy version={__version__}")
        return 0
    print(DEVELOPMENT_MESSAGE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

