"""Pair this laptop device with the development backend."""

import argparse
from pathlib import Path

from app.auth.credentials import CredentialStore
from app.auth.device_identity import get_or_create_device_id
from app.auth.pairing import PairingClient
from app.config import AppConfig
from app.data.repo import Repository


def main() -> int:
    config = AppConfig()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=config.database_path)
    parser.add_argument("--base-url", default=config.api_base_url)
    parser.add_argument("--credentials", type=Path, default=config.credential_path)
    parser.add_argument("--device-name", default="Assessment Device")
    parser.add_argument("--poll-interval", type=float, default=2.0)
    parser.add_argument("--timeout", type=float, default=600.0)
    args = parser.parse_args()
    if not args.base_url:
        parser.error("Set ASSESS_API_URL or --base-url")
    with Repository(args.db) as repository:
        device_id = get_or_create_device_id(repository)
    store = CredentialStore(args.credentials)
    with PairingClient(args.base_url) as client:
        pairing = client.request(device_id, args.device_name)
        print("Device pairing\n")
        print(f"Device ID:\n{device_id}\n")
        print(f"Pairing code:\n{pairing.code}\n")
        print("Waiting for approval...")
        client.wait_and_claim(
            pairing, store, device_id, interval=args.poll_interval, timeout=args.timeout
        )
    print("Pairing successful.\nDevice credential stored.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
