"""Central, Pi-friendly visual tokens for the student assessment UI."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Theme:
    background: tuple[int, int, int] = (245, 248, 250)
    surface: tuple[int, int, int] = (255, 255, 255)
    panel: tuple[int, int, int] = (255, 255, 255)
    foreground: tuple[int, int, int] = (25, 38, 51)
    muted: tuple[int, int, int] = (90, 105, 118)
    accent: tuple[int, int, int] = (27, 103, 160)
    accent_text: tuple[int, int, int] = (255, 255, 255)
    hover: tuple[int, int, int] = (230, 240, 247)
    selected: tuple[int, int, int] = (218, 238, 250)
    review: tuple[int, int, int] = (255, 224, 130)
    correct: tuple[int, int, int] = (199, 239, 207)
    wrong: tuple[int, int, int] = (255, 205, 210)
    danger: tuple[int, int, int] = (190, 48, 55)
    success: tuple[int, int, int] = (37, 125, 76)
    warning: tuple[int, int, int] = (166, 104, 19)
    border: tuple[int, int, int] = (67, 85, 99)
    disabled: tuple[int, int, int] = (211, 218, 223)
    disabled_text: tuple[int, int, int] = (112, 124, 134)
    focus: tuple[int, int, int] = (242, 126, 32)
    padding: int = 16
    gap: int = 10
    border_width: int = 2
    focus_width: int = 4
    corner_radius: int = 12
    minimum_target: int = 48
    title_size: int = 36
    heading_size: int = 28
    result_size: int = 48
    body_size: int = 26
    option_size: int = 24
    button_size: int = 24
    small_size: int = 20


THEME = Theme()
