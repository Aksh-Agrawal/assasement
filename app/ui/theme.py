"""Central visual constants for the Phase 7A desktop prototype."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Theme:
    background: tuple[int, int, int] = (243, 247, 250)
    surface: tuple[int, int, int] = (255, 255, 255)
    panel: tuple[int, int, int] = (255, 255, 255)
    foreground: tuple[int, int, int] = (25, 35, 45)
    muted: tuple[int, int, int] = (90, 105, 118)
    accent: tuple[int, int, int] = (18, 105, 168)
    accent_text: tuple[int, int, int] = (255, 255, 255)
    hover: tuple[int, int, int] = (230, 240, 247)
    selected: tuple[int, int, int] = (184, 224, 250)
    review: tuple[int, int, int] = (255, 224, 130)
    correct: tuple[int, int, int] = (199, 239, 207)
    wrong: tuple[int, int, int] = (255, 205, 210)
    danger: tuple[int, int, int] = (190, 48, 55)
    border: tuple[int, int, int] = (67, 85, 99)
    disabled: tuple[int, int, int] = (211, 218, 223)
    disabled_text: tuple[int, int, int] = (112, 124, 134)
    focus: tuple[int, int, int] = (242, 126, 32)
    padding: int = 16
    gap: int = 10
    border_width: int = 2
    focus_width: int = 4
    corner_radius: int = 7
    minimum_target: int = 48
    heading_size: int = 28
    result_size: int = 34
    body_size: int = 21
    option_size: int = 18
    button_size: int = 18
    small_size: int = 15


THEME = Theme()
