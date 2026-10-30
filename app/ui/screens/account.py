"""Distinct student/profile identity and technical device trust."""
from app.auth.product_state import account_status
from app.ui.components import choice_button, header
from app.ui.layout import Rect
from app.ui.screens.common import paragraph


def render(surface, c, fonts):
    controls = []
    header(surface, controls, "ACCOUNT & PROFILES", c, fonts)
    account = c.repository.get_student_account_context()
    state = account_status(c.repository,
        verified_this_run=bool(c.device and c.device.account_verified),
        busy=bool(c.device and c.device.busy and c.device.operation.startswith("account_")))
    rows = (
        "Account: " + (account["display_name"] if account else "Not connected"),
        state,
        c.network_label + " / Sync: " + (f"{c.pending_sync_count} pending" if c.pending_sync_count else "No pending attempts"),
        f"Study Profiles: {len(c.profiles)} / 3 - manage on the website",
        "Offline practice uses your last synchronized Study Profiles.",
    )
    for i, value in enumerate(rows):
        paragraph(surface, value, Rect(24, 72 + i * 32, 752, 30), fonts.small, max_lines=1)
    for i in range(len(c.choices)):
        choice_button(surface, controls, c, fonts, i,
                      Rect(24 + (i % 2) * 380, 250 + (i // 2) * 72, 360, 64))
    return controls
