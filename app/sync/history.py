"""Download profile-authorized completed summaries, never native assessment sessions."""

import json

from app.content.client import ContentAuthError, ContentNetworkError, ProfileUnavailableError


def sync_history(repository, api):
    failures = review_failures = synced = skipped = results = 0
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
                # History and Analytics can refresh even if review evidence fails.
                fetch_detail = getattr(client, "fetch_completed_result_detail", None)
                if not callable(fetch_detail):
                    continue
                items = repository.completed_results(profile.id)
                enriched = False
                for item in items:
                    local = repository.get_attempt(item["attempt_id"])
                    if (local and local.profile_id == profile.id) or "review_available" in item:
                        continue
                    try:
                        detail = fetch_detail(item["attempt_id"])
                    except (ContentAuthError, ProfileUnavailableError):
                        raise
                    except ContentNetworkError as error:
                        review_failures += 1
                        repository.set_setting("last_history_error", type(error).__name__)
                        break
                    except Exception as error:
                        review_failures += 1
                        repository.set_setting("last_history_error", type(error).__name__)
                        continue
                    if detail is not None:
                        if any(detail.get(field) != item.get(field) for field in
                               ("attempt_id", "study_profile_id", "source", "status")):
                            review_failures += 1
                            repository.set_setting("last_history_error", "ReviewIdentityMismatch")
                            continue
                        item["review"] = detail.get("review", [])
                        item["review_available"] = bool(detail.get("review_available"))
                        enriched = True
                if enriched:
                    try:
                        repository.cache_completed_results(profile.id, context["link_id"], items)
                    except ValueError as error:
                        review_failures += 1
                        repository.set_setting("last_history_error", type(error).__name__)
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
         "results": results, "failures": failures, "review_failures": review_failures}))
    return failures == 0 and review_failures == 0
