"""Document-aligned device screens; all controls emit canonical actions."""

from app.ui.components import (
    choice_button,
    header,
)
from app.ui.layout import Rect
from app.ui.screens.common import text


def render(surface, c, fonts):
    controls = []
    header(surface, controls, "SETTINGS > ACCOUNT / PAIR", c, fonts)
    paired = bool(c.device and c.device.credentials.load_safe())
    for i, value in enumerate(
        (
            "Device: " + ("Paired" if paired else "Not paired"),
            "Account: " + ("Linked device credential available" if paired else "Not linked"),
            "Device ID: " + c.repository.get_or_create_device_id()[:8],
        )
    ):
        text(surface, value, (24, 100 + i * 60), fonts.body)
    if not c.device or not c.device.config.api_base_url:
        text(surface, "Online account services are not configured yet.", (24, 284), fonts.small)
    for i in range(len(c.choices)):
        choice_button(surface, controls, c, fonts, i, Rect(24 + i * 256, 342, 240, 64))
    return controls
