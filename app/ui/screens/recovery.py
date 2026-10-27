"""Non-destructive local startup recovery; no raw exception text."""

from app.input.actions import Action
from app.ui.layout import Rect
from app.ui.screens.common import button, paragraph, text
from app.ui.theme import THEME


def render(surface, session, fonts, *, mode="recovery", message=""):
    controls = []
    text(surface, "DEVICE NEEDS ATTENTION", (24, 24), fonts.title, color=THEME.danger)
    value = {
        "recovery": "Local storage could not be opened safely.\n\nYour existing assessment data has not been deleted.\n\nSupport code: DB-001",
        "diagnostics": "LOCAL STARTUP DIAGNOSTICS\n\n"
        + "\n".join(f"{r.label}: {r.detail}" for r in session.rows[-6:]),
        "options": "RECOVERY OPTIONS\n\nRetry after checking storage and power.\nKeep the existing database and question packs.\nAsk support to restore a verified backup following docs/RECOVERY.md.\nNo files have been removed or replaced.",
    }[mode]
    paragraph(surface, value, Rect(24, 102, 752, 240), fonts.body)
    for i, (label, payload) in enumerate(
        (("Retry", "retry"), ("Diagnostics", "diagnostics"), ("Recovery options", "options"))
    ):
        button(
            surface,
            controls,
            Rect(24 + i * 256, 358, 240, 64),
            label,
            Action.CONFIRM,
            fonts,
            payload=("recovery", payload),
        )
    text(
        surface,
        message or "A Retry   B Diagnostics   C Recovery options   Esc Exit",
        (24, 452),
        fonts.small,
        color=THEME.muted,
    )
    return controls
