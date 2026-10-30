"""Document-aligned device screens; all controls emit canonical actions."""

from app.ui.components import (
    choice_list,
    header,
)
from app.ui.screens import text_entry
from app.ui.screens.common import text
from app.ui.theme import THEME


def render(surface, c, fonts):
    if c.selected_wifi:
        return text_entry.render(surface, c, fonts)
    controls = []
    header(surface, controls, "SETTINGS > WI-FI", c, fonts)
    wifi = "Connected" if c.device and c.device.wifi_connected else "Offline / unverified"
    internet = c.device.internet_status if c.device else "Unknown"
    text(surface, f"Wi-Fi: {wifi} / Internet: {internet}", (24, 74), fonts.small)
    if not c.device or not c.device.wifi.available:
        text(
            surface,
            "Wi-Fi controls unavailable on this platform.",
            (24, 104),
            fonts.small,
            color=THEME.warning,
        )
    choice_list(surface, controls, c, fonts, top=134, rows=3, height=64)
    return controls
