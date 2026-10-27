"""Validate and summarize a local question-pack JSON file."""

import argparse
from pathlib import Path

from app.content.validator import PackValidationError, validate_pack


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pack", type=Path)
    parser.add_argument("--expected-sha256")
    return parser.parse_args()


def _print_error(error: PackValidationError) -> None:
    print("INVALID PACK")
    for issue in error.issues:
        print(f"\n[{issue.code}]\n{issue.path}\n{issue.message}")


def main() -> int:
    args = _arguments()
    try:
        validated = validate_pack(args.pack, expected_sha256=args.expected_sha256)
    except PackValidationError as error:
        _print_error(error)
        return 1
    summary = validated.summary
    print(
        f"VALID PACK\n\nSet:\n{summary.set_id}\n\nVersion:\n{summary.version}\n\n"
        f"Title:\n{summary.title}\n\nSubject:\n{summary.subject}\n\n"
        f"Chapter:\n{summary.chapter}\n\nQuestions:\n{summary.questions}\n\n"
        f"SHA-256:\n{summary.sha256}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
