"""Institute assignments remain separate from personal My Library."""
from app.ui.components import choice_list, header
from app.ui.screens.common import text


def render(surface, c, fonts):
    controls = []
    header(surface, controls, "PRACTICE > INSTITUTE WORK", c, fonts)
    text(surface, "Assigned work for this linked study profile", (24, 74), fonts.body)
    choice_list(surface, controls, c, fonts)
    return controls
