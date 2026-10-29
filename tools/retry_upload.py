"""Operator-only requeue of one retained completed failed upload; evidence stays unchanged."""
import argparse
from uuid import UUID

from app.config import AppConfig
from app.data.repo import Repository


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("attempt_id", type=UUID)
    args = parser.parse_args()
    config = AppConfig()
    try:
        if not config.database_path.is_file():
            raise FileNotFoundError("Existing device database required")
        with Repository(config.database_path) as repository:
            repository.requeue_failed_attempt(str(args.attempt_id))
        print("Exact retained UUID requeued. Cloud authorization will be checked again.")
        return 0
    except Exception as error:
        print("Requeue unavailable: " + type(error).__name__)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
