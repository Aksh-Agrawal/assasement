"""Report non-sensitive device health; network checks are explicitly opt-in."""

import argparse
import json
from pathlib import Path

from app.auth.credentials import CredentialStore
from app.config import AppConfig
from app.data.repo import Repository
from app.diagnostics import (
    HealthLevel,
    collect_device_status,
    collect_network_status,
)
from app.update.activation import ActivationManager


def collect(args: argparse.Namespace) -> dict:
    credential_store = CredentialStore(args.credentials)
    credential = credential_store.load_safe()
    network = (
        collect_network_status(
            args.base_url,
            auth_token=credential.token if credential else None,
            connect_timeout=args.connect_timeout,
            read_timeout=args.read_timeout,
        )
        if args.network
        else None
    )
    if not args.db.is_file():
        return {
            "diagnostic_schema_version": 1,
            "schema_version": None,
            "health": HealthLevel.ERROR.value,
            "error_codes": ["DB-001"],
            "local_db_status": "missing",
            "offline_assessment_ready": False,
        }
    try:
        with Repository(args.db) as repository:
            status = collect_device_status(
                repository,
                database_path=args.db,
                credential_store=credential_store,
                update_manager=ActivationManager(args.update_root),
                trusted_signing_key_id=args.trusted_key_id,
                network=network,
            )
        result = status.to_dict()
        result["api_configuration"] = "Configured" if args.base_url else "Not configured"
        return result
    except Exception:
        return {
            "diagnostic_schema_version": 1,
            "schema_version": None,
            "health": HealthLevel.ERROR.value,
            "error_codes": ["DB-001"],
            "local_db_status": "error",
            "offline_assessment_ready": False,
        }


def _human(status: dict) -> None:
    print(f"API configuration: {status.get('api_configuration', 'Not configured')}")
    print(f"Health: {status['health']}")
    print(f"Support codes: {', '.join(status.get('error_codes', ())) or 'none'}")
    print(f"Application version: {status.get('app_version', 'unknown')}")
    print(f"Local DB health: {status.get('local_db_status', 'unknown')}")
    print(f"DB schema version: {status.get('schema_version', 'unknown')}")
    print(f"DB size bytes: {status.get('database_size_bytes', 0)}")
    print(f"Device identity present: {'yes' if status.get('device_id_present') else 'no'}")
    print(f"Paired: {'yes' if status.get('paired') else 'no'}")
    print(f"Pending sync: {status.get('completed_pending_sync', 0)}")
    print(f"Syncing: {status.get('syncing_count', 0)}")
    print(f"Failed sync: {status.get('failed_sync_count', 0)}")
    print(f"Auth-required sync: {status.get('auth_required_count', 0)}")
    print(f"Last sync success: {status.get('last_sync_success') or 'never'}")
    print(f"Last sync attempt: {status.get('last_sync_attempt') or 'never'}")
    print(f"Last sync failure: {status.get('last_sync_failure') or 'never'}")
    print(f"Installed packs: {status.get('installed_content_count', 0)}")
    print(f"Installed versions: {', '.join(status.get('installed_content_versions', ())) or 'none'}")
    print(f"Active versions: {', '.join(status.get('active_content_versions', ())) or 'none'}")
    print(f"Last content sync: {status.get('last_content_sync') or 'never'}")
    print(f"Current software release: {status.get('current_release', 'unknown')}")
    print(f"Staged update: {status.get('staged_release') or 'none'}")
    print(f"Last update status: {status.get('last_update_status', 'unknown')}")
    print(
        "Offline assessment readiness: "
        f"{'YES' if status.get('offline_assessment_ready') else 'NO'}"
    )
    network = status.get("network")
    if network and network.get("checked"):
        print(f"Backend reachable: {'yes' if network.get('backend_reachable') else 'no'}")
        print(f"Backend database ready: {'yes' if network.get('database_ready') else 'no'}")
        print(f"Authentication accepted: {'yes' if network.get('auth_accepted') else 'no'}")
        print(f"Content catalog reachable: {'yes' if network.get('catalog_reachable') else 'no'}")
        print(
            "Update endpoint reachable: "
            f"{'yes' if network.get('update_endpoint_reachable') else 'no'}"
        )


def parser() -> argparse.ArgumentParser:
    config = AppConfig()
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--db", type=Path, default=config.database_path)
    result.add_argument("--credentials", type=Path, default=config.credential_path)
    result.add_argument("--base-url", default=config.api_base_url)
    result.add_argument("--update-root", type=Path, default=config.update_root)
    result.add_argument("--trusted-key-id", default=config.trusted_update_key_id)
    result.add_argument("--connect-timeout", type=float, default=config.sync_connect_timeout)
    result.add_argument("--read-timeout", type=float, default=config.sync_read_timeout)
    result.add_argument("--network", action="store_true")
    result.add_argument("--json", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    status = collect(args)
    if args.json:
        print(json.dumps(status, sort_keys=True, separators=(",", ":")))
    else:
        _human(status)
    if status["health"] == HealthLevel.ERROR.value:
        return 2
    return 0 if status["health"] == HealthLevel.OK.value else 1


if __name__ == "__main__":
    raise SystemExit(main())
