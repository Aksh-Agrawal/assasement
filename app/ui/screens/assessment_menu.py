"""Document-aligned device screens; all controls emit canonical actions."""

from app.ui.components import (
    choice_list,
    header,
)
from app.ui.screens.common import text


def render(surface, c, fonts):
    controls = []
    header(surface, controls, "ASSESSMENT MENU", c, fonts)
    answered, unanswered, _ = c.submit_counts
    text(surface, f"Progress: {answered} / {answered + unanswered} answered", (24, 74), fonts.body)
    choice_list(surface, controls, c, fonts, rows=3)
    return controls
