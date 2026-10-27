"""Document-aligned device screens; all controls emit canonical actions."""

from app.ui.components import (
    choice_button,
    header,
)
from app.ui.layout import Rect
from app.ui.screens.common import text


def render(surface, c, fonts):
    controls = []
    header(surface, controls, "RETURN HOME?", c, fonts)
    text(surface, "Your test will stay available to resume.", (24, 100), fonts.heading)
    text(
        surface,
        "Answers, confidence and review flags are saved on this device.",
        (24, 146),
        fonts.body,
    )
    for i in range(2):
        choice_button(surface, controls, c, fonts, i, Rect(24, 230 + i * 90, 752, 72))
    return controls
