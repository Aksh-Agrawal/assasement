"""Student-safe device and sync status."""

import pygame

from app.ui.controller import UIController
from app.ui.screens.common import Control, Fonts, text, top_bar
from app.ui.theme import THEME


def render(surface: pygame.Surface, controller: UIController, fonts: Fonts) -> list[Control]:
    controls: list[Control] = []
    top_bar(surface, controls, "Device status", fonts, network=controller.network_label)
    integrity = controller.repository.quick_check().ok
    rows = (
        ("Storage", "Ready" if integrity else "Needs attention", integrity),
        (
            "Question packs",
            f"{len(controller.question_sets)} installed",
            bool(controller.question_sets),
        ),
        (
            "Account",
            "Paired"
            if controller.selected_profile and controller.selected_profile.server_user_id
            else "Local profile",
            True,
        ),
        ("Internet", controller.network_label, controller.network_label == "Online"),
        (
            "Sync",
            f"{controller.pending_sync_count} pending"
            if controller.pending_sync_count
            else "Up to date",
            not controller.pending_sync_count,
        ),
        ("Software", f"v{controller.software_version}", True),
    )
    for index, (label, value, good) in enumerate(rows):
        y = 82 + index * 54
        text(surface, label, (70, y), fonts.body)
        text(
            surface,
            "OK" if good else "!",
            (420, y),
            fonts.body,
            color=THEME.success if good else THEME.warning,
        )
        text(surface, value, (460, y), fonts.body, color=THEME.foreground)
    if controller.network_label == "Offline":
        text(
            surface,
            "Assessments remain available and save safely on this device.",
            (70, 420),
            fonts.small,
            color=THEME.muted,
        )
    return controls
