"""Document-aligned device screens; all controls emit canonical actions."""

from app.input.actions import Action
from app.ui.components import (
    header,
)
from app.ui.layout import Rect
from app.ui.screens.common import button, text
from app.ui.theme import THEME


def render(surface, c, fonts):
    controls = []
    header(surface, controls, "READY TO SUBMIT?", c, fonts)
    answered, unanswered, marked = c.submit_counts
    for i, value in enumerate(
        (f"Answered: {answered}", f"Unanswered: {unanswered}", f"Marked for review: {marked}")
    ):
        text(surface, value, (24, 100 + i * 48), fonts.heading)
    text(surface, "Your answers are saved locally.", (24, 270), fonts.body, color=THEME.muted)
    button(surface, controls, Rect(24, 342, 360, 64), "Continue Test", Action.BACK, fonts)
    button(
        surface,
        controls,
        Rect(408, 342, 368, 64),
        "Submit Assessment",
        Action.SUBMIT,
        fonts,
        state="danger",
    )
    return controls
