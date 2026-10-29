"""Profile-specific eligibility around the existing exact-byte installation pipeline."""
from app.content.client import ContentAuthError, ContentProtocolError
from app.content.sync import ContentSyncStatus, PackSyncResult, _install_one


def refresh_library(repository, client, profile_id, link_id):
    try:
        catalog = client.fetch_catalog()
    except ContentAuthError:
        repository.revoke_profile_library(profile_id)
        raise
    repository.cache_profile_library(profile_id, link_id, client.catalog_metadata)
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
        result = _install_one(repository, client, pack, temp_directory=temp_directory,
                              max_pack_bytes=max_pack_bytes)
    if result.status is ContentSyncStatus.AUTH_REQUIRED:
        repository.revoke_profile_library(profile_id)
    # Delivery acknowledgement is distinct from the durable installation and local grant.
    try:
        client.acknowledge(pack, "downloaded" if result.status in {
            ContentSyncStatus.INSTALLED, ContentSyncStatus.ALREADY_PRESENT} else "failed")
    except ContentAuthError:
        repository.revoke_profile_library(profile_id)
    except Exception:
        pass  # A retry uses verified local bytes and repeats acknowledgement.
    return result


def sync_profile_deliveries(repository, api, config):
    """Bounded rotating work prevents one profile or cached pack starving another."""
    import json
    jobs = []
    for profile in repository.list_profiles():
        context = repository.get_profile_link_context(profile.id)
        if profile.link_state != "linked" or not context:
            continue
        try:
            with api.content(local_profile_id=profile.id, link_id=context["link_id"]) as client:
                packs = refresh_library(repository, client, profile.id, context["link_id"])
                jobs.extend((profile.id, context["link_id"], pack) for pack in packs)
        except Exception as error:
            repository.set_setting("last_profile_library_check",
                                   json.dumps({"state": "UNAVAILABLE", "kind": type(error).__name__}))
    if not jobs:
        return
    try:
        cursor = int(repository.get_setting("profile_library_delivery_cursor") or "0") % len(jobs)
    except (ValueError, TypeError):
        cursor = 0
    count = min(config.content_max_downloads_per_cycle, len(jobs))
    for i in range(count):
        profile_id, link_id, pack = jobs[(cursor + i) % len(jobs)]
        try:
            with api.content(local_profile_id=profile_id, link_id=link_id) as client:
                download_for_profile(repository, client, profile_id, link_id, pack,
                    temp_directory=config.content_download_directory,
                    max_pack_bytes=config.content_max_pack_bytes)
        except Exception as error:
            repository.set_setting("last_profile_library_check",
                                   json.dumps({"state": "UNAVAILABLE", "kind": type(error).__name__}))
    repository.set_setting("profile_library_delivery_cursor", str((cursor + count) % len(jobs)))
