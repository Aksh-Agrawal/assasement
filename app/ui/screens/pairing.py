"""Document-aligned device screens; all controls emit canonical actions."""

from app.input.actions import Action
from app.ui.components import (
    choice_button,
    header,
)
from app.ui.layout import Rect
from app.ui.screens.common import button, paragraph, text
from app.ui.theme import THEME


def render(surface, c, fonts):
    controls = []
    header(surface, controls, "CONNECT YOUR DEVICE", c, fonts)
    text(surface, "Sign in on the website > Account & Devices", (24, 96), fonts.heading)
    pairing_request = c.device.pairing if c.device else None
    if pairing_request:
        text(surface, pairing_request.code, (260, 178), fonts.result, color=THEME.accent)
        paragraph(surface, "Choose Connect Raspberry Pi and enter this code.",
                  Rect(24, 250, 752, 42), fonts.body, max_lines=1)
    else:
        revoked = c.repository.get_setting("account_connection_state") == "revoked"
        paragraph(surface,
            "This device is no longer connected to your account. Reconnect to continue syncing. Assessment data is retained."
            if revoked else "Connect this Raspberry Pi to your account. Generate a code when the cloud is available.",
            Rect(24, 150, 752, 120), fonts.body, max_lines=3)
    choice_button(surface, controls, c, fonts, 0, Rect(24, 300, 360, 48))
    choice_button(surface, controls, c, fonts, 1, Rect(404, 300, 372, 48))
    button(surface, controls, Rect(24, 366, 216, 48), "Cancel", Action.BACK, fonts)
    text(
        surface,
        "Existing study profiles remain usable offline.",
        (264, 382),
        fonts.small,
        color=THEME.muted,
    )
    return controls
