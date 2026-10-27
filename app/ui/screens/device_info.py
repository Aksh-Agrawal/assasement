"""Document-aligned device screens; all controls emit canonical actions."""

from app.ui.components import (
    choice_button,
    header,
)
from app.ui.layout import Rect
from app.ui.screens.common import text
from app.ui.theme import THEME


def render(surface, c, fonts):
    controls = []
    header(surface, controls, "DEVICE / STORAGE", c, fonts)
    rows = (
        c.device.device_rows(c.repository)
        if c.device
        else (
            ("Software", c.software_version),
            ("Device", c.repository.get_or_create_device_id()[:8]),
        )
    )
    for i, (label, value) in enumerate(rows):
        text(surface, label, (24, 84 + i * 34), fonts.body, color=THEME.muted)
        text(surface, value, (280, 84 + i * 34), fonts.body)
    text(surface, f"Attempt queue: {c.pending_sync_count} pending", (24, 342), fonts.body)
    choice_button(surface, controls, c, fonts, 0, Rect(544, 366, 232, 48))
    return controls
