"""Document-aligned device screens; all controls emit canonical actions."""

from app.ui.components import (
    choice_button,
    header,
)
from app.ui.layout import Rect
from app.ui.screens.common import paragraph, text
from app.ui.theme import THEME


def render(surface, c, fonts):
    controls = []
    header(surface, controls, "TEST SETUP", c, fonts)
    selected = c.selected_question_set
    if selected:
        paragraph(surface, selected.title, Rect(24, 76, 752, 58), fonts.heading, max_lines=2)
        text(
            surface,
            f"{len(selected.questions)} questions   |   Version {selected.version}",
            (24, 142),
            fonts.body,
        )
        text(surface, "MARKING", (24, 190), fonts.small, color=THEME.muted)
        text(
            surface,
            f"{selected.marking.correct:+g} Correct       {selected.marking.wrong:+g} Incorrect       {selected.marking.skip:g} Skipped",
            (24, 216),
            fonts.body,
        )
        text(surface, "Confidence: Sure / Not Sure / Guessing", (24, 262), fonts.body)
        text(
            surface,
            "Your progress is saved automatically on this device.",
            (24, 302),
            fonts.body,
            color=THEME.muted,
        )
        if c.can_resume:
            text(
                surface,
                "An unfinished test exists. Resume keeps its original pack version.",
                (24, 334),
                fonts.small,
                color=THEME.warning,
            )
        choice_button(surface, controls, c, fonts, 0, Rect(24, 366, 360, 48), primary=True)
        if c.can_resume:
            choice_button(surface, controls, c, fonts, 1, Rect(408, 366, 368, 48))
    return controls
