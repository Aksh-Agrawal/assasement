"""Shared pygame drawing primitives; controls emit canonical actions only."""

from dataclasses import dataclass

import pygame

from app.input.actions import Action
from app.ui.layout import Rect, wrap_text
from app.ui.theme import THEME


@dataclass(frozen=True, slots=True)
class Control:
    rect: Rect
    action: Action
    label: str


@dataclass(slots=True)
class Fonts:
    heading: pygame.font.Font
    body: pygame.font.Font
    option: pygame.font.Font
    button: pygame.font.Font
    small: pygame.font.Font
    result: pygame.font.Font


def make_fonts() -> Fonts:
    """Use pygame's bundled default font, avoiding machine-specific paths."""
    return Fonts(
        heading=pygame.font.Font(None, THEME.heading_size),
        body=pygame.font.Font(None, THEME.body_size),
        option=pygame.font.Font(None, THEME.option_size),
        button=pygame.font.Font(None, THEME.button_size),
        small=pygame.font.Font(None, THEME.small_size),
        result=pygame.font.Font(None, THEME.result_size),
    )


def text(
    surface: pygame.Surface,
    value: str,
    position: tuple[int, int],
    font: pygame.font.Font,
    *,
    color: tuple[int, int, int] = THEME.foreground,
) -> None:
    surface.blit(font.render(value, True, color), position)


def paragraph(
    surface: pygame.Surface,
    value: str,
    rect: Rect,
    font: pygame.font.Font,
    *,
    color: tuple[int, int, int] = THEME.foreground,
    max_lines: int | None = None,
) -> None:
    lines = wrap_text(value, lambda line: font.size(line)[0], rect.width, max_lines=max_lines)
    line_height = font.get_linesize()
    for index, line in enumerate(lines):
        if rect.y + (index + 1) * line_height > rect.y + rect.height:
            break
        text(surface, line, (rect.x, rect.y + index * line_height), font, color=color)


def button(
    surface: pygame.Surface,
    controls: list[Control],
    rect: Rect,
    label: str,
    action: Action,
    fonts: Fonts,
    *,
    state: str = "normal",
    enabled: bool = True,
) -> None:
    fills = {
        "normal": THEME.surface,
        "selected": THEME.selected,
        "review": THEME.review,
        "correct": THEME.correct,
        "wrong": THEME.wrong,
        "danger": THEME.danger,
        "focus": THEME.hover,
        "disabled": THEME.disabled,
    }
    effective_state = state if enabled else "disabled"
    fill = fills[effective_state]
    label_color = (
        THEME.accent_text
        if effective_state == "danger"
        else THEME.disabled_text
        if effective_state == "disabled"
        else THEME.foreground
    )
    target = pygame.Rect(rect.x, rect.y, rect.width, rect.height)
    pygame.draw.rect(surface, fill, target, border_radius=THEME.corner_radius)
    border_width = THEME.focus_width if effective_state == "focus" else THEME.border_width
    border_color = THEME.focus if effective_state == "focus" else THEME.border
    pygame.draw.rect(
        surface, border_color, target, border_width, border_radius=THEME.corner_radius
    )
    lines = wrap_text(label, lambda line: fonts.button.size(line)[0], rect.width - 16, max_lines=2)
    line_height = fonts.button.get_linesize()
    y = rect.y + (rect.height - len(lines) * line_height) // 2
    for line in lines:
        rendered = fonts.button.render(line, True, label_color)
        surface.blit(rendered, (rect.x + 10, y))
        y += line_height
    if enabled:
        controls.append(Control(rect, action, label))


def title(surface: pygame.Surface, value: str, fonts: Fonts) -> None:
    text(surface, value, (THEME.padding, 12), fonts.heading)


def status(surface: pygame.Surface, value: str, fonts: Fonts) -> None:
    if value:
        paragraph(surface, value, Rect(16, 447, 768, 25), fonts.small, color=THEME.muted)
