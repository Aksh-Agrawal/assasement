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
    header(surface, controls, "DIAGNOSTICS", c, fonts)
    state = c.device.diagnostics if c.device else None
    if state:
        rows = (
            ("Local DB", state.local_db_status),
            ("Schema", str(state.schema_version)),
            ("Device identity", "Ready" if state.device_id_present else "Needs attention"),
            ("Question content", f"{state.installed_content_count} packs"),
            ("Sync queue", f"{state.completed_pending_sync + state.failed_sync_count} pending"),
            ("API", "Not configured" if not c.device.config.api_base_url else c.network_label),
            ("Credential", "Paired" if state.paired else "Not paired"),
        )
        for i, (label, value) in enumerate(rows):
            text(surface, label, (24, 80 + i * 34), fonts.body, color=THEME.muted)
            text(surface, value, (300, 80 + i * 34), fonts.body)
        text(
            surface, "Support: " + (", ".join(state.error_codes) or "NONE"), (24, 328), fonts.small
        )
    else:
        text(surface, "Run a local check. Internet is not required.", (24, 100), fonts.body)
    for i in range(2):
        choice_button(surface, controls, c, fonts, i, Rect(24 + i * 384, 366, 368, 48))
    return controls
