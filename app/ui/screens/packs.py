"""Document-aligned device screens; all controls emit canonical actions."""

from app.ui.components import (
    choice_list,
    header,
)
from app.ui.layout import Rect
from app.ui.screens.common import paragraph


def render(surface, c, fonts):
    controls = []
    header(surface, controls, f"{c.selected_subject} > QUESTION SETS", c, fonts)
    paragraph(
        surface,
        c.selected_chapter or "Select question set",
        Rect(24, 72, 752, 30),
        fonts.body,
        max_lines=1,
    )
    choice_list(surface, controls, c, fonts)
    return controls
