"""Account-authorized device profile cache; transport credentials are not ownership."""

import json
from datetime import UTC, datetime
from uuid import UUID

import httpx

from app.api.transport import create_client, json_object
from app.auth.profile_links import ProfileLinkClient, ProfileLinkError
from app.connectivity import ObservedTransport
from app.core.models import Profile


def unlink_relationship(config, credentials, repository, *, scope=None, profile_id=None, transport=None):
    """Persist the exact target before I/O so an interrupted request can be replayed."""
    pending = json.loads(repository.get_setting("pending_unlink") or "null")
    account = repository.get_student_account_context()
    if pending:
        if scope and (scope != pending["scope"] or profile_id != pending.get("profile_id")):
            raise ValueError("An unlink is already pending")
    elif scope:
        pending = {"scope": scope, "account_id": account["cloud_account_id"] if account else None}
        if scope == "profile":
            profile = repository.get_profile(profile_id)
            link = repository.get_profile_link_context(profile_id)
            if (not profile or profile.ownership_state != "owned" or not link
                    or (account and profile.cloud_account_id != pending["account_id"])):
                repository.fail_unlink(scope)
                raise ProfileLinkError("LINK_OWNERSHIP_MISMATCH")
            if profile.link_state != "linked":
                retired = json.loads(repository.get_setting("unavailable_profile:" + profile_id) or "{}")
                if retired.get("reason") == "explicit_unlink" and retired.get("link_id") == link["link_id"]:
                    return "confirmed"
                repository.fail_unlink(scope)
                raise ProfileLinkError("LINK_PROFILE_CONFLICT")
            pending.update(profile_id=profile_id, link_id=link["link_id"], study_profile_id=profile.cloud_profile_id)
        elif not account:
            raise ValueError("No student account is connected")
        repository.set_setting("pending_unlink", json.dumps(pending))
    else:
        return None

    try:
        if pending["account_id"] != (account["cloud_account_id"] if account else None):
            raise ValueError("The connected account changed")
        if not pending.get("confirmed"):
            credential = credentials.load_safe()
            if not credential:
                raise ValueError("The device credential is unavailable")
            observed = ObservedTransport(repository.database_path, transport)
            if pending["scope"] == "profile":
                with ProfileLinkClient(config.api_base_url, auth_token=credential.token, transport=observed,
                        connect_timeout=config.sync_connect_timeout, read_timeout=config.sync_read_timeout) as client:
                    result = client.unlink(pending["profile_id"], pending["link_id"])
                profile = repository.get_profile(pending["profile_id"])
                if (result.get("status") != "revoked" or result.get("link_id") != pending["link_id"]
                        or result.get("local_profile_id") != pending["profile_id"]
                        or result.get("study_profile_id") != pending["study_profile_id"]
                        or not profile or result.get("student_account_id") != profile.cloud_account_id):
                    raise ValueError("The server did not confirm the requested profile unlink")
            else:
                with create_client(config.api_base_url, auth_token=credential.token, transport=observed,
                        connect_timeout=config.sync_connect_timeout, read_timeout=config.sync_read_timeout) as client:
                    response = client.post("/api/v1/device-account/disconnect",
                                           params={"account_id": pending["account_id"]})
                    response.raise_for_status()
                    if json_object(response).get("status") != "disconnected":
                        raise ValueError("The server did not confirm the account disconnect")
        if pending["scope"] == "profile":
            repository.finish_profile_unlink(pending["profile_id"])
        else:
            # Record confirmation before removing the credential needed to replay.
            repository.set_setting("pending_unlink", json.dumps({**pending, "confirmed": True}))
            credentials.clear()
            repository.clear_student_account_context(disconnected=True)
        return "confirmed"
    except httpx.RequestError:
        return "pending"
    except ProfileLinkError as error:
        if error.code == "LINK_NETWORK":
            return "pending"
        repository.fail_unlink(pending["scope"])
        raise
    except (httpx.HTTPStatusError, ValueError):
        repository.fail_unlink(pending["scope"])
        raise


def sync_account(config, credentials, repository, *, create=None, disconnect=False, transport=None):
    if disconnect:
        return unlink_relationship(config, credentials, repository, scope="account", transport=transport)
    if repository.get_setting("pending_unlink"):
        raise RuntimeError("Finish the pending unlink before refreshing profiles.")
    repository.set_setting("account_connection_state", "verification_required")
    try:
        result = _sync_account(config, credentials, repository, create=create, transport=transport)
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
        repository.set_setting("account_connection_state", "connected")
        return result


def _sync_account(config, credentials, repository, *, create=None, transport=None):
    credential = credentials.load_safe()
    if not credential:
        raise RuntimeError("Connect this Raspberry Pi to your account.")
    with create_client(
        config.api_base_url, auth_token=credential.token, transport=ObservedTransport(repository.database_path, transport)
    ) as client:
        if create:
            response = client.post("/api/v1/device-account/profiles", json=create)
            response.raise_for_status()
        response = client.get("/api/v1/device-account")
        response.raise_for_status()
        data = response.json()
    UUID(data["account_id"])
    if not isinstance(data["display_name"], str) or not data["display_name"].strip():
        raise ValueError("Invalid cloud account name")
    rows = data["profiles"]
    for p in rows:
        UUID(p["id"])
        UUID(p["link_id"])
        if (p["account_id"] != data["account_id"] or not isinstance(p["local_profile_id"], str)
                or not p["local_profile_id"].strip() or len(p["local_profile_id"]) > 255
                or (p["local_profile_id"].startswith("cloud-") and p["local_profile_id"] != "cloud-" + p["id"])):
            raise ValueError("Invalid cloud profile identity")
        if not isinstance(p["name"], str) or not p["name"].strip():
            raise ValueError("Invalid cloud profile name")
        existing = repository.get_profile(p["local_profile_id"])
        if existing and (existing.cloud_account_id != data["account_id"]
                         or existing.cloud_profile_id != p["id"]):
            raise ValueError("Cloud profile identity collision")
    active_ids = {p["local_profile_id"] for p in rows}
    if len(active_ids) != len(rows) or len({p["id"] for p in rows}) != len(rows):
        raise ValueError("Duplicate cloud profile identity")
    retired = blocked = 0
    for profile in repository.list_profiles():
        if (profile.ownership_state == "owned" and profile.link_state == "linked"
                and profile.id not in active_ids):
            repository.retire_profile_link(profile.id, reason="absent_from_account")
            retired += 1
    # Reuse the server's mapping, including explicitly linked legacy IDs.
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
        repository.update_cloud_profile_name(local_id, data["account_id"], p["name"])
        unavailable = json.loads(repository.get_setting("unavailable_profile:" + local_id) or "{}")
        if (unavailable.get("reason") in {"profile_forbidden", "explicit_unlink"}
                and unavailable.get("link_id") == p["link_id"]):
            blocked += 1
            continue
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
        repository.set_setting("unavailable_profile:" + local_id, "{}")
    repository.set_setting("last_profile_reconciliation", json.dumps(
        {"available": len(rows) - blocked, "retired": retired, "authorization_skipped": blocked}))
    previous_account = repository.get_student_account_context()
    if previous_account is None or previous_account["cloud_account_id"] != data["account_id"]:
        repository.delete_setting("unlink_message")
    repository.set_setting("account_profiles", json.dumps(data))
    repository.cache_student_account_context(
        data["account_id"], data["display_name"], last_verified_at=datetime.now(UTC)
    )
    return data
