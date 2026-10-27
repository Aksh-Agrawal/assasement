"""Validate and atomically install a local question pack into development SQLite."""

import argparse
from pathlib import Path

from app.content.importer import PackImportError, import_pack
from app.content.validator import PackValidationError, validate_pack
from app.data.repo import Repository


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pack", type=Path)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--inactive",
        action="store_true",
        help="install without making this version active",
    )
    return parser.parse_args()


def _show_validation_error(error: PackValidationError) -> None:
    print("IMPORT REJECTED")
    for issue in error.issues:
        print(f"\n[{issue.code}] {issue.path}\n{issue.message}")


def main() -> int:
    args = _arguments()
    if args.dry_run:
        try:
            validated = validate_pack(args.pack, expected_sha256=args.expected_sha256)
        except PackValidationError as error:
            _show_validation_error(error)
            return 1
        summary = validated.summary
        print(
            f"DRY RUN VALID\nSet: {summary.set_id}\nVersion: {summary.version}\n"
            f"Questions: {summary.questions}\nSHA-256: {summary.sha256}\nDatabase unchanged."
        )
        return 0

    try:
        with Repository(args.db) as repository:
            result = import_pack(
                args.pack,
                repository,
                expected_sha256=args.expected_sha256,
                make_active=not args.inactive,
            )
    except PackValidationError as error:
        _show_validation_error(error)
        return 1
    except PackImportError as error:
        print(f"IMPORT REJECTED\n\n[{error.code}]\n{error.message}")
        return 1

    summary = result.pack.summary
    print(
        f"PACK IMPORTED\nSet: {summary.set_id}\nVersion: {summary.version}\n"
        f"Questions: {summary.questions}\nSHA-256: {summary.sha256}\n"
        f"Active: {'yes' if result.active else 'no'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
