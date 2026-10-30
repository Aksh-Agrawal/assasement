"""Dedicated institute grants using the existing pack verification/import pipeline."""

from contextlib import contextmanager
from uuid import UUID

import httpx

from app.content.catalog import RemotePack
from app.content.client import (
    ContentApiClient,
    ContentAuthError,
    ContentNetworkError,
    ContentProtocolError,
    ProfileUnavailableError,
)
from app.content.sync import ContentSyncStatus, PackSyncResult, _install_one


class InstituteContentClient(ContentApiClient):
    def fetch_work(self):
        try:
            response = self._client.get(
                f"/api/v1/institute-content/{self.link_id}/catalog",
                params={"local_profile_id": self.local_profile_id},
            )
        except httpx.RequestError as error:
            raise ContentNetworkError("Institute work unavailable") from error
        self._check_response(response)
        try:
            body = response.json()
            items = body["packs"]
            if body["schema_version"] != 1 or not isinstance(items, list) or len(items) > 1000:
                raise ValueError()
            seen = set()
            for item in items:
                RemotePack.from_dict(item)
                for key in ("assignment_id", "institute_id", "membership_id", "study_profile_id"):
                    UUID(item[key])
                if item["assignment_id"] in seen:
                    raise ValueError()
                seen.add(item["assignment_id"])
            return items
        except (ValueError, KeyError, TypeError) as error:
            raise ContentProtocolError("Invalid institute work") from error

    @contextmanager
    def stream_pack(self, pack):
        try:
            with self._client.stream(
                "GET",
                f"/api/v1/institute-content/{self.link_id}/packs/{self.assignment_id}",
                params={"local_profile_id": self.local_profile_id},
            ) as response:
                self._check_response(response)
                yield response
        except httpx.RequestError as error:
            raise ContentNetworkError("Institute content unavailable") from error


def refresh_work(repository, client, profile_id, link_id):
    try:
        items = client.fetch_work()
    except ContentAuthError:
        repository.revoke_institute_work(profile_id)
        raise
    repository.cache_institute_work(profile_id, link_id, items)
    return items


def download_work(
    repository, client, profile_id, link_id, assignment_id, *, temp_directory, max_pack_bytes
):
    items = refresh_work(repository, client, profile_id, link_id)
    item = next((a for a in items if a["assignment_id"] == assignment_id), None)
    if item is None:
        raise ContentProtocolError("Assignment is no longer eligible")
    pack = RemotePack.from_dict(item)
    existing = repository.get_question_set_persistence(pack.set_id, pack.version)
    if existing:
        if existing.content_hash != pack.sha256:
            raise ContentProtocolError("Cached pack hash mismatch")
        return PackSyncResult(pack.set_id, pack.version, ContentSyncStatus.ALREADY_PRESENT)
    client.assignment_id = assignment_id
    return _install_one(
        repository, client, pack, temp_directory=temp_directory, max_pack_bytes=max_pack_bytes
    )


def sync_institute_work(repository, api, config):
    budget = config.content_max_downloads_per_cycle
    failures = 0
    for profile in repository.list_profiles():
        context = repository.get_profile_link_context(profile.id)
        if not context or profile.link_state != "linked":
            continue
        try:
            with api.institute_content(
                local_profile_id=profile.id, link_id=context["link_id"]
            ) as client:
                items = refresh_work(repository, client, profile.id, context["link_id"])
                for item in items:
                    if budget <= 0:
                        break
                    if repository.get_question_set(item["set_id"], item["version"]):
                        continue
                    download_work(
                        repository,
                        client,
                        profile.id,
                        context["link_id"],
                        item["assignment_id"],
                        temp_directory=config.content_download_directory,
                        max_pack_bytes=config.content_max_pack_bytes,
                    )
                    budget -= 1
        except ProfileUnavailableError:
            repository.retire_profile_link(profile.id, reason="profile_forbidden")
        except ContentAuthError:
            raise
        except Exception as error:
            failures += 1
            repository.set_setting("last_institute_error", type(error).__name__)
    return failures == 0
