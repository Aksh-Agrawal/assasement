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
    header(surface, controls, "SETTINGS > SOFTWARE UPDATE", c, fonts)
    available = c.device.available_update if c.device else None
    text(surface, f"Installed: {c.software_version}", (24, 92), fonts.heading)
    text(
        surface,
        f"Available: {available.manifest.version if available else 'Not checked'}",
        (24, 136),
        fonts.body,
    )
    text(
        surface,
        "Updates are verified before staging. Attempts and packs are preserved.",
        (24, 186),
        fonts.body,
    )
    text(
        surface,
        "Installation is not available on this device yet. Ask support to finish setup.",
        (24, 220),
        fonts.small,
        color=THEME.muted,
    )
    for i in range(3):
        choice_button(surface, controls, c, fonts, i, Rect(24 + i * 256, 320, 240, 72))
    return controls
