"""Explicit local-profile confirmation before any network submission."""
from app.ui.components import choice_button, header
from app.ui.layout import Rect
from app.ui.screens.common import paragraph, text


def render(surface, c, fonts):
    controls = []
    header(surface, controls, "LINK THIS LOCAL PROFILE?", c, fonts)
    paragraph(surface, "Local profile: " + c.selected_profile.display_name,
              Rect(24, 96, 752, 80), fonts.heading, max_lines=2)
    text(surface, "Code: " + c.text_value, (24, 208), fonts.heading)
    text(surface, "Claim/link this profile only. Older attempts stay unclaimed.", (24, 280), fonts.body)
    for i in range(len(c.choices)):
        choice_button(surface, controls, c, fonts, i, Rect(24 + i * 360, 350, 336, 60))
    return controls
