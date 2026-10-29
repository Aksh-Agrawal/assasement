"""Document-aligned device screens; all controls emit canonical actions."""

from app.ui.components import (
    choice_button,
    header,
)
from app.ui.layout import Rect
from app.ui.screens.common import paragraph, text
from app.ui.theme import THEME


def render(surface, c, fonts):
    controls = []
    header(surface, controls, "SETTINGS > SYNC", c, fonts)
    rows = (
        ("Server", "Not configured" if not c.device or not c.device.config.api_base_url
         else "Reachable" if c.device.network and c.device.network.backend_reachable else "Offline"),
        ("Pairing", "Paired" if c.device and c.device.credentials.load_safe() else "Not paired"),
        ("Completed attempts pending", str(c.pending_sync_count)),
        ("Last successful sync", c.repository.get_setting("last_sync_success") or "Not yet synced"),
    )
    for i, (name, value) in enumerate(rows):
        text(surface, name, (24, 94 + i * 56), fonts.small, color=THEME.muted)
        paragraph(surface, value, Rect(24, 118 + i * 56, 752, 32), fonts.body, max_lines=1)
    summary = c.repository.sync_diagnostic_summary()
    if summary["attention_required"]:
        text(surface, "Sync attention required. Data retained; contact your operator.",
             (24, 316), fonts.small, color=THEME.muted)
    for i in range(len(c.choices)):
        choice_button(surface, controls, c, fonts, i, Rect(24 + i * 256, 342, 240, 64))
    return controls
