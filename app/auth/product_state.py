"""Student-facing account state; cached identity is never proof of a live connection."""

from datetime import UTC, datetime


def account_status(repository, *, verified_this_run=False, busy=False, now=None):
    context = repository.get_student_account_context()
    state = repository.get_setting("account_connection_state")
    if state == "revoked":
        return "Reconnection required"
    if not context:
        return "Not connected"
    if busy:
        return "Verifying"
    stamp = context.get("last_verified_at")
    try:
        verified = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        age = ((now or datetime.now(UTC)) - verified).total_seconds()
    except (ValueError, TypeError, AttributeError):
        age = -1
    if state == "connected" and verified_this_run and 0 <= age < 180:
        return "Connected"
    if state == "offline_cached":
        return "Offline - last verified " + (stamp or "time unavailable")
    if state == "error":
        return "Needs attention - cached profiles available"
    return "Verification required - cached profiles available"
