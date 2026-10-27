"""Boot console showing only completed real checks and the next pending check."""

from app.ui.layout import Rect
from app.ui.screens.common import paragraph, progress_bar, text
from app.ui.theme import THEME


def render(surface, session, fonts):
    text(surface, "ASSESS DEVICE", (24, 24), fonts.title)
    text(surface, "Starting device...", (24, 78), fonts.heading)
    for i, row in enumerate(session.rows):
        y = 124 + i * 28
        text(
            surface,
            "+" if row.ok else "!",
            (24, y),
            fonts.body,
            color=THEME.success if row.ok else THEME.warning,
        )
        text(surface, row.label, (56, y), fonts.body)
        paragraph(
            surface,
            row.detail,
            Rect(322, y + 2, 452, 26),
            fonts.small,
            max_lines=1,
            color=THEME.muted,
        )
    progress_bar(surface, Rect(24, 406, 752, 10), len(session.rows) / 9)
    text(
        surface,
        "Local startup | Network is not required",
        (24, 448),
        fonts.small,
        color=THEME.muted,
    )
    return []
