"""Distinct student/profile identity and technical device trust."""
from app.ui.components import choice_button, header
from app.ui.layout import Rect
from app.ui.screens.common import paragraph


def render(surface, c, fonts):
    controls = []
    header(surface, controls, "SETTINGS > ACCOUNT / PROFILES", c, fonts)
    paired = bool(c.device and c.device.credentials.load_safe())
    account = c.repository.get_student_account_context()
    rows = (
        "Account: " + (account["display_name"] if account else "Not connected"),
        "Profiles: " + (", ".join(p.display_name for p in c.profiles) or "None synced"),
        "Device connection: " + ("Connected" if account and paired else "Connect your Raspberry Pi"),
        "Create profiles online; cached profiles and downloads work offline.",
    )
    for i, value in enumerate(rows):
        paragraph(surface, value, Rect(24, 72 + i * 36, 752, 32), fonts.body, max_lines=1)
    for i in range(len(c.choices)):
        choice_button(surface, controls, c, fonts, i,
                      Rect(24 + (i % 2) * 380, 228 + (i // 2) * 64, 360, 54))
    return controls
