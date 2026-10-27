"""Document-aligned device screens; all controls emit canonical actions."""

import pygame

from app.ui.components import (
    header,
    scroll_controls,
)
from app.ui.layout import Rect
from app.ui.screens.common import paragraph, text
from app.ui.theme import THEME


def render(surface, c, fonts):
    controls = []
    header(surface, controls, "PROGRESS / RECENT 20", c, fonts)
    items = c.history_items
    c.scroll = min(c.scroll, max(0, len(items) - 3))
    if not items:
        text(surface, "No completed assessments yet.", (24, 110), fonts.heading)
        text(
            surface,
            "Your local history will appear here, including pending sync.",
            (24, 154),
            fonts.body,
        )
    for index, item in enumerate(items[c.scroll : c.scroll + 3]):
        y = 88 + index * 90
        pygame.draw.rect(surface, THEME.surface, pygame.Rect(24, y, 752, 80), border_radius=8)
        paragraph(
            surface,
            f"{item.subject} / {item.title}",
            Rect(40, y + 10, 560, 26),
            fonts.body,
            max_lines=1,
        )
        date = item.completed_at.strftime("%d %b") if item.completed_at else ""
        text(
            surface,
            f"{date}   |   {item.sync_status.value.replace('_', ' ').title()}",
            (40, y + 46),
            fonts.small,
            color=THEME.muted,
        )
        text(
            surface,
            f"{item.score:g} / {item.maximum:g}",
            (620, y + 28),
            fonts.heading,
            color=THEME.accent,
        )
    if len(items) > 3:
        scroll_controls(surface, controls, c, fonts, c.scroll > 0, c.scroll < len(items) - 3)
    return controls
