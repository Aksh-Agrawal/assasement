"""Account-authorized device profile cache; transport credentials are not ownership."""

import json
from datetime import UTC, datetime
from uuid import UUID

import httpx

from app.api.transport import create_client
from app.core.models import Profile


def sync_account(config, credentials, repository, *, create=None, disconnect=False, transport=None):
    repository.set_setting("account_connection_state", "verification_required")
    try:
        result = _sync_account(config, credentials, repository, create=create,
                               disconnect=disconnect, transport=transport)
    except httpx.RequestError:
        repository.set_setting("account_connection_state", "offline_cached"
                               if repository.get_student_account_context() else "error")
        raise
    except httpx.HTTPStatusError as error:
        if error.response.status_code in {401, 403}:
            repository.clear_student_account_context()
            repository.set_setting("account_connection_state", "revoked")
        else:
            repository.set_setting("account_connection_state", "error")
        raise
    else:
        repository.set_setting("account_connection_state", "not_connected" if disconnect else "connected")
        return result


def _sync_account(config, credentials, repository, *, create=None, disconnect=False, transport=None):
    credential = credentials.load_safe()
    if not credential:
        raise RuntimeError("Connect this Raspberry Pi to your account.")
    from app.connectivity import ObservedTransport

    with create_client(
        config.api_base_url, auth_token=credential.token, transport=ObservedTransport(repository.database_path, transport)
    ) as client:
        if disconnect:
            response = client.post("/api/v1/device-account/disconnect")
            response.raise_for_status()
            repository.clear_student_account_context()
            credentials.clear()
            return None
        if create:
            response = client.post("/api/v1/device-account/profiles", json=create)
            response.raise_for_status()
        response = client.get("/api/v1/device-account")
        if response.status_code in {401, 403}:
            repository.clear_student_account_context()
        response.raise_for_status()
        data = response.json()
    UUID(data["account_id"])
    rows = data["profiles"]
    for p in rows:
        UUID(p["id"])
        UUID(p["link_id"])
        if p["account_id"] != data["account_id"] or p["local_profile_id"] != "cloud-" + p["id"]:
            raise ValueError("Invalid cloud profile identity")
    # Preserve legacy records and historical links. Only cloud-derived IDs are touched.
    for p in rows:
        local_id = p["local_profile_id"]
        existing = repository.get_profile(local_id)
        if existing is None:
            repository.create_profile(
                Profile(
                    id=local_id,
                    display_name=p["name"],
                    cloud_account_id=data["account_id"],
                    cloud_profile_id=p["id"],
                    ownership_state="owned",
                    link_state="unlinked",
                )
            )
        elif (
            existing.cloud_account_id != data["account_id"] or existing.cloud_profile_id != p["id"]
        ):
            raise ValueError("Cloud profile identity collision")
        repository.update_cloud_profile_name(local_id, data["account_id"], p["name"])
        old = repository.get_profile_link_context(local_id)
        if old and old["link_id"] != p["link_id"]:
            repository.apply_profile_link(
                local_id,
                {
                    "status": "revoked",
                    "link_id": old["link_id"],
                    "student_account_id": data["account_id"],
                    "study_profile_id": p["id"],
                    "local_profile_id": local_id,
                    "account_display_name": data["display_name"],
                    "study_profile_name": p["name"],
                },
            )
        repository.apply_profile_link(
            local_id,
            {
                "status": "linked",
                "link_id": p["link_id"],
                "student_account_id": data["account_id"],
                "study_profile_id": p["id"],
                "local_profile_id": local_id,
                "account_display_name": data["display_name"],
                "study_profile_name": p["name"],
            },
        )
    repository.set_setting("account_profiles", json.dumps(data))
    repository.cache_student_account_context(
        data["account_id"], data["display_name"], last_verified_at=datetime.now(UTC)
    )
    return data
