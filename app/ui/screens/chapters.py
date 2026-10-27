"""Document-aligned device screens; all controls emit canonical actions."""

from app.ui.components import (
    choice_list,
    header,
)
from app.ui.screens.common import text


def render(surface, c, fonts):
    controls = []
    header(surface, controls, f"{c.selected_subject} > CHAPTERS", c, fonts)
    text(surface, "Select chapter", (24, 74), fonts.body)
    choice_list(surface, controls, c, fonts)
    return controls
