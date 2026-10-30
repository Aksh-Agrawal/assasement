"""Profile-specific eligibility around the existing exact-byte installation pipeline."""
import json

from app.content.catalog import RemotePack
from app.content.client import ContentAuthError, ContentProtocolError
from app.content.sync import ContentSyncStatus, PackSyncResult, _install_one


def _report(repository, client, profile_id, pack, status):
    try:
        client.acknowledge(pack, status)
    except ContentAuthError:
        repository.revoke_profile_library(profile_id)
    except Exception:
        # The next rotating delivery cycle rechecks installed bytes and retries.
        repository.set_setting("delivery_ack_pending", "1")


def refresh_library(repository, client, profile_id, link_id):
    try:
        catalog = client.fetch_catalog()
    except ContentAuthError:
        repository.revoke_profile_library(profile_id)
        raise
    repository.cache_profile_library(profile_id, link_id, client.catalog_metadata)
    for pack in catalog.packs:
        _report(repository, client, profile_id, pack, "device_seen")
    return catalog.packs


def download_for_profile(repository, client, profile_id, link_id, pack, *,
                         temp_directory, max_pack_bytes):
    # Refresh server eligibility before using either shared cached bytes or downloading.
    remote = refresh_library(repository, client, profile_id, link_id)
    approved = next((p for p in remote if (p.set_id, p.version) == (pack.set_id, pack.version)), None)
    if approved is None or approved.sha256 != pack.sha256:
        raise ContentProtocolError("Content is no longer eligible")
    existing = repository.get_question_set(pack.set_id, pack.version)
    if existing is not None:
        persistence = repository.get_question_set_persistence(pack.set_id, pack.version)
        if persistence.content_hash != pack.sha256:
            raise ContentProtocolError("Cached content hash mismatch")
        result = PackSyncResult(pack.set_id, pack.version, ContentSyncStatus.ALREADY_PRESENT)
    else:
        _report(repository, client, profile_id, pack, "downloading")
        result = _install_one(repository, client, pack, temp_directory=temp_directory,
                              max_pack_bytes=max_pack_bytes,
                              on_downloaded=lambda: _report(
                                  repository, client, profile_id, pack, "downloaded"))
    if result.status is ContentSyncStatus.AUTH_REQUIRED:
        repository.revoke_profile_library(profile_id)
    # Delivery acknowledgement is distinct from the durable installation and local grant.
    try:
        client.acknowledge(pack, "installed" if result.status in {
            ContentSyncStatus.INSTALLED, ContentSyncStatus.ALREADY_PRESENT} else "failed")
    except ContentAuthError:
        repository.revoke_profile_library(profile_id)
    except Exception:
        pass  # A retry uses verified local bytes and repeats acknowledgement.
    return result


def sync_profile_deliveries(repository, api, config):
    """Bounded rotating work prevents one profile or cached pack starving another."""
    jobs = []
    failures = 0
    for profile in repository.list_profiles():
        context = repository.get_profile_link_context(profile.id)
        if profile.link_state != "linked" or not context:
            continue
        try:
            with api.content(local_profile_id=profile.id, link_id=context["link_id"]) as client:
                changes = client.fetch_changes() if hasattr(client, "fetch_changes") else None
                key = "profile_manifest:" + context["link_id"]
                cached = json.loads(repository.get_setting(key) or "{}")
                removals = changes.get("removals", []) if changes else []
                for operation in removals:
                    client.acknowledge_removal(operation, "device_seen")
                    client.acknowledge_removal(operation, "removing")
                if changes is None or changes["snapshot_token"] != cached.get("token") or removals:
                    try:
                        packs = refresh_library(repository, client, profile.id, context["link_id"])
                    except Exception:
                        for operation in removals:
                            try:
                                client.acknowledge_removal(operation, "failed")
                            except Exception:
                                pass  # The persisted operation is retried after reconnection.
                        raise
                    if changes:
                        repository.set_setting(key, json.dumps({"token": changes["snapshot_token"],
                                                               "packs": client.catalog_metadata}))
                else:
                    packs = tuple(RemotePack.from_dict(p) for p in cached.get("packs", []))
                    repository.cache_profile_library(profile.id, context["link_id"], cached.get("packs", []))
                try:
                    for operation in removals:
                        if any(p["set_id"] == operation["set_id"]
                               for p in repository.profile_library_catalog(profile.id)):
                            raise ContentProtocolError("Removal is inconsistent with desired catalogue")
                        repository.reconcile_content_state(profile.id)
                        client.acknowledge_removal(operation, "removed")
                except Exception:
                    for operation in removals:
                        try:
                            client.acknowledge_removal(operation, "failed")
                        except Exception:
                            pass
                    raise
                states = {i["set_id"]: i["status"] for i in changes.get("installations", [])} if changes else {}
                jobs.extend((profile.id, context["link_id"], pack) for pack in packs
                            if states.get(pack.set_id) != "installed"
                            or repository.get_question_set(pack.set_id, pack.version) is None)
        except Exception as error:
            failures += 1
            repository.set_setting("last_profile_library_check",
                                   json.dumps({"state": "UNAVAILABLE", "kind": type(error).__name__}))
    if not jobs:
        return failures == 0
    try:
        cursor = int(repository.get_setting("profile_library_delivery_cursor") or "0") % len(jobs)
    except (ValueError, TypeError):
        cursor = 0
    count = min(config.content_max_downloads_per_cycle, len(jobs))
    for i in range(count):
        profile_id, link_id, pack = jobs[(cursor + i) % len(jobs)]
        try:
            with api.content(local_profile_id=profile_id, link_id=link_id) as client:
                result = download_for_profile(repository, client, profile_id, link_id, pack,
                    temp_directory=config.content_download_directory,
                    max_pack_bytes=config.content_max_pack_bytes)
                if result.status not in {ContentSyncStatus.INSTALLED, ContentSyncStatus.ALREADY_PRESENT}:
                    failures += 1
        except Exception as error:
            failures += 1
            repository.set_setting("last_profile_library_check",
                                   json.dumps({"state": "UNAVAILABLE", "kind": type(error).__name__}))
    repository.set_setting("profile_library_delivery_cursor", str((cursor + count) % len(jobs)))

    return failures == 0
