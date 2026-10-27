"""Document-aligned device screens; all controls emit canonical actions."""

from app.input.actions import Action
from app.ui.components import (
    choice_button,
    header,
)
from app.ui.layout import Rect
from app.ui.screens.common import button, text
from app.ui.theme import THEME


def render(surface, c, fonts):
    controls = []
    header(surface, controls, "PAIR DEVICE", c, fonts)
    text(surface, "Enter this code on your account.", (24, 96), fonts.heading)
    pairing_request = c.device.pairing if c.device else None
    if pairing_request:
        text(surface, pairing_request.code, (260, 178), fonts.result, color=THEME.accent)
        text(surface, "Waiting for approval...", (260, 260), fonts.body)
    else:
        text(
            surface,
            "Pairing requires a configured server and network.",
            (24, 160),
            fonts.body,
            color=THEME.muted,
        )
        choice_button(surface, controls, c, fonts, 0, Rect(24, 236, 752, 64))
    button(surface, controls, Rect(24, 366, 216, 48), "Cancel", Action.BACK, fonts)
    text(
        surface,
        "Existing local profiles remain available offline.",
        (264, 382),
        fonts.small,
        color=THEME.muted,
    )
    return controls
