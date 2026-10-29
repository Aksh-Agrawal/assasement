"""Distinct student/profile identity and technical device trust."""
from app.ui.components import choice_button, header
from app.ui.layout import Rect
from app.ui.screens.common import paragraph


def render(surface, c, fonts):
    controls = []
    header(surface, controls, "SETTINGS > ACCOUNT / PROFILES", c, fonts)
    profile = c.selected_profile
    context = c.repository.get_profile_link_context(profile.id) if profile else None
    paired = bool(c.device and c.device.credentials.load_safe())
    rows = (
        "Account: " + (context["account_display_name"] if context else "Unclaimed"),
        "Study profile: " + (context["study_profile_name"] if context else "Unclaimed"),
        "Local: " + (profile.display_name if profile else "None") +
        " / " + (profile.link_state if profile else "unlinked"),
        "Device: " + ("Authenticated" if paired else "Device authentication required"),
    )
    for i, value in enumerate(rows):
        paragraph(surface, value, Rect(24, 72 + i * 36, 752, 32), fonts.body, max_lines=1)
    for i in range(len(c.choices)):
        choice_button(surface, controls, c, fonts, i,
                      Rect(24 + (i % 2) * 380, 228 + (i // 2) * 64, 360, 54))
    return controls
