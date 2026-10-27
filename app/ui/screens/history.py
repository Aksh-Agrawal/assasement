"""Local, offline-capable assessment history."""

import pygame

from app.ui.controller import UIController
from app.ui.screens.common import Control, Fonts, empty_state, text, top_bar
from app.ui.theme import THEME


def render(surface: pygame.Surface, controller: UIController, fonts: Fonts) -> list[Control]:
    controls: list[Control] = []
    top_bar(surface, controls, "Recent assessments", fonts, network=controller.network_label)
    items = controller.history_items
    if not items:
        empty_state(
            surface,
            "No results yet",
            "Completed assessments will appear here, even while this device is offline.",
            fonts,
        )
        return controls
    for index, item in enumerate(items[:4]):
        y = 72 + index * 88
        pygame.draw.rect(surface, THEME.surface, pygame.Rect(28, y, 744, 72), border_radius=10)
        text(surface, item.title, (48, y + 10), fonts.body)
        date = item.completed_at.strftime("%d %b") if hasattr(item.completed_at, "strftime") else ""
        text(surface, f"{item.subject}  |  {date}", (48, y + 42), fonts.small, color=THEME.muted)
        score = f"{item.score:g} / {item.maximum:g}" if item.score is not None else "-"
        rendered = fonts.heading.render(score, True, THEME.accent)
        surface.blit(rendered, (590, y + 8))
        sync = "Synced" if item.sync_status.value == "synced" else "Pending sync"
        text(
            surface,
            sync,
            (610, y + 44),
            fonts.small,
            color=THEME.success if sync.startswith("Synced") else THEME.warning,
        )
    return controls
