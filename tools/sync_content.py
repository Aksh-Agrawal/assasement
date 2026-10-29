"""Run one authenticated, bounded remote question-content sync cycle."""

import argparse
from pathlib import Path

from app.auth.credentials import CredentialStore
from app.config import AppConfig
from app.content.client import ContentApiClient
from app.content.sync import sync_content_once
from app.data.repo import Repository


def main() -> int:
    config = AppConfig()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=config.database_path)
    parser.add_argument("--base-url", default=config.api_base_url)
    parser.add_argument("--credentials", type=Path, default=config.credential_path)
    parser.add_argument("--temp-dir", type=Path, default=config.content_download_directory)
    parser.add_argument("--limit", type=int, default=config.content_max_downloads_per_cycle)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--profile", help="Linked local profile ID for personal library sync")
    args = parser.parse_args()
    if not args.base_url:
        parser.error("--base-url is required when no API base URL is configured")
    credential = CredentialStore(args.credentials).load_safe()
    with Repository(args.db) as repository:
        if args.profile:
            profile = repository.get_profile(args.profile)
            context = repository.get_profile_link_context(args.profile)
            if not profile or profile.link_state != "linked" or not context:
                parser.error("--profile must identify an explicitly linked local profile")
            from app.content.profile_library import download_for_profile, refresh_library
            with ContentApiClient(
                args.base_url, auth_token=credential.token if credential else None,
                local_profile_id=args.profile, link_id=context["link_id"],
            ) as client:
                packs = refresh_library(repository, client, args.profile, context["link_id"])
                for pack in packs[:args.limit]:
                    if args.dry_run:
                        print(f"{pack.set_id} v{pack.version} available")
                    else:
                        result = download_for_profile(
                            repository, client, args.profile, context["link_id"], pack,
                            temp_directory=args.temp_dir, max_pack_bytes=config.content_max_pack_bytes)
                        print(f"{pack.set_id} v{pack.version} {result.status.value}")
            return 0
    with Repository(args.db) as repository, ContentApiClient(
        args.base_url,
        auth_token=credential.token if credential else None,
        connect_timeout=config.sync_connect_timeout,
        read_timeout=config.sync_read_timeout,
    ) as client:
        result = sync_content_once(
            repository,
            client,
            temp_directory=args.temp_dir,
            max_pack_bytes=config.content_max_pack_bytes,
            max_downloads_per_cycle=args.limit,
            dry_run=args.dry_run,
        )
    print(f"Remote catalog: {result.catalog_count} packs")
    print(f"Installed locally: {result.installed_before}")
    print(f"New/missing versions: {result.eligible_count}")
    if result.status:
        print(result.status.value)
    for item in sorted(result.packs, key=lambda value: (value.set_id, value.version)):
        print(f"{item.set_id} v{item.version:<4} {item.status.value}")
    return 0 if result.status is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
