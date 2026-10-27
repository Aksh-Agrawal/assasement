"""Document-aligned device screens; all controls emit canonical actions."""

from app.ui.components import (
    choice_button,
    header,
)
from app.ui.layout import Rect
from app.ui.screens.common import text


def render(surface, c, fonts):
    controls = []
    header(surface, controls, "ABOUT", c, fonts)
    text(surface, "Assessment Device", (24, 100), fonts.title)
    text(surface, f"Software v{c.software_version}", (24, 162), fonts.body)
    text(surface, "Target: Raspberry Pi Zero 2 W", (24, 210), fonts.body)
    text(surface, f"Content: {len(c.question_sets)} installed versions", (24, 258), fonts.body)
    choice_button(surface, controls, c, fonts, 0, Rect(24, 354, 280, 64))
    return controls
