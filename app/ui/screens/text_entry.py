"""Document-aligned device screens; all controls emit canonical actions."""

import pygame

from app.input.actions import Action
from app.ui.components import (
    header,
    keyboard,
)
from app.ui.layout import Rect
from app.ui.router import UIScreen
from app.ui.screens.common import button, paragraph, text
from app.ui.theme import THEME


def render(surface, c, fonts):
    controls = []
    is_pin = c.screen is UIScreen.PIN
    label = (
        "LINK STUDY PROFILE"
        if c.screen is UIScreen.LINK_PROFILE
        else "PIN UNLOCK"
        if is_pin
        else "CREATE CLOUD STUDY PROFILE"
        if c.screen is UIScreen.ADD_PROFILE
        else "WI-FI PASSWORD"
    )
    header(surface, controls, label, c, fonts)
    prompt = (
        "Local profile: " + c.selected_profile.display_name
        if c.screen is UIScreen.LINK_PROFILE
        else c.selected_profile.display_name
        if is_pin
        else "Profile name"
        if c.screen is UIScreen.ADD_PROFILE
        else c.selected_wifi[0]
    )
    paragraph(surface, prompt, Rect(24, 72, 752, 32), fonts.heading, max_lines=1)
    hidden = is_pin or c.screen is UIScreen.WIFI and not c.show_password
    value = "*" * len(c.text_value) if hidden else c.text_value
    pygame.draw.rect(surface, THEME.surface, pygame.Rect(24, 112, 568, 44), border_radius=6)
    text(
        surface,
        value[-40:] or ("Enter PIN" if is_pin else "Type here"),
        (36, 124),
        fonts.body,
        color=THEME.muted if not value else THEME.foreground,
    )
    keyboard(surface, controls, c, fonts, pin=is_pin)
    if is_pin:
        button(
            surface,
            controls,
            Rect(24, 366, 216, 48),
            "Forgot PIN?",
            Action.CONFIRM,
            fonts,
            payload=("command", "forgot"),
        )
    elif c.screen is UIScreen.WIFI:
        button(
            surface,
            controls,
            Rect(24, 366, 128, 48),
            "Hide" if c.show_password else "Show",
            Action.CONFIRM,
            fonts,
            payload=("command", "show"),
        )
        button(
            surface,
            controls,
            Rect(168, 366, 128, 48),
            "Forget",
            Action.CONFIRM,
            fonts,
            payload=("command", "wifi_forget"),
        )
    return controls
