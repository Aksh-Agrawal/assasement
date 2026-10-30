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
