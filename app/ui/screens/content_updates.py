"""Document-aligned device screens; all controls emit canonical actions."""

from app.ui.components import (
    choice_list,
    header,
)
from app.ui.screens.common import text


def render(surface, c, fonts):
    controls = []
    header(surface, controls, "SETTINGS > CONTENT", c, fonts)
    text(
        surface, ("Cloud not configured | local packs remain available"
                  if not c.device or not c.device.config.api_base_url
                  else "Question content | downloaded packs stay available offline"), (24, 74), fonts.body
    )
    choice_list(surface, controls, c, fonts)
    return controls
