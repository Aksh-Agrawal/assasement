"""Download profile-authorized completed summaries, never native assessment sessions."""

import json

from app.content.client import ContentAuthError, ProfileUnavailableError


def sync_history(repository, api):
    failures = synced = skipped = results = 0
    for profile in repository.list_profiles():
        context = repository.get_profile_link_context(profile.id)
        if profile.link_state != "linked" or not context:
            continue
        try:
            with api.content(local_profile_id=profile.id, link_id=context["link_id"]) as client:
                items = client.fetch_completed_results()
                # Do not round-trip attempts whose richer native evidence already
                # exists locally. Web (and other linked-device) attempts get their
                # completed-only answer review cached beside the summary.
                fetch_detail = getattr(client, "fetch_completed_result_detail", None)
                for item in items:
                    local = repository.get_attempt(item["attempt_id"])
                    if (local and local.profile_id == profile.id) or not callable(fetch_detail):
                        continue
                    detail = fetch_detail(item["attempt_id"])
                    if detail is not None:
                        item["review"] = detail.get("review", [])
                        item["review_available"] = bool(detail.get("review_available"))
            repository.cache_completed_results(profile.id, context["link_id"], items)
            synced += 1
            results += len(items)
        except ProfileUnavailableError:
            repository.retire_profile_link(profile.id, reason="profile_forbidden")
            skipped += 1
        except ContentAuthError:
            raise
        except Exception as error:
            failures += 1
            repository.set_setting("last_history_error", type(error).__name__)
    repository.set_setting("last_history_summary", json.dumps(
        {"profiles_synced": synced, "profiles_skipped": skipped,
         "results": results, "failures": failures}))
    return failures == 0
