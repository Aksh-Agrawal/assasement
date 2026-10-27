"""Run one bounded attempt-sync cycle or inspect eligible payloads without mutation."""

import argparse
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from app.auth.credentials import CredentialStore
from app.config import AppConfig
from app.data.repo import Repository
from app.sync.client import SyncApiClient
from app.sync.payloads import build_upload_payload
from app.sync.policy import SyncPolicy
from app.sync.worker import SyncWorker


def _arguments() -> argparse.Namespace:
    config = AppConfig()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=config.database_path)
    parser.add_argument("--base-url", default=config.api_base_url)
    parser.add_argument("--batch-size", type=int, default=config.sync_batch_size)
    parser.add_argument("--max-retries", type=int, default=config.sync_max_automatic_retries)
    parser.add_argument("--connect-timeout", type=float, default=config.sync_connect_timeout)
    parser.add_argument("--read-timeout", type=float, default=config.sync_read_timeout)
    parser.add_argument("--credentials", type=Path, default=Path("var/device_credentials.json"))
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    policy = SyncPolicy(
        batch_size=args.batch_size,
        max_automatic_retries=args.max_retries,
    )
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    with Repository(args.db) as repository:
        if args.dry_run:
            attempts = repository.get_sync_eligible_attempts(
                now=datetime.now(UTC),
                limit=policy.batch_size,
                max_attempts=policy.max_automatic_retries,
            )
            for attempt in attempts:
                print(json.dumps(build_upload_payload(repository, attempt.id), sort_keys=True))
            print(f"Dry run: {len(attempts)} attempt(s) eligible; no state changed.")
            return 0

        if not args.base_url:
            raise SystemExit("--base-url is required unless --dry-run is used")
        credential = CredentialStore(args.credentials).load_safe()
        token = credential.token if credential else None
        with SyncApiClient(
            args.base_url,
            connect_timeout=args.connect_timeout,
            read_timeout=args.read_timeout,
            auth_token=token,
        ) as client:
            result = SyncWorker(repository, client, policy=policy).run_sync_once()
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
