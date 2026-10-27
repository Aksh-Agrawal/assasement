"""Framework-neutral logical layout and text helpers for the 800x480 UI."""

from collections.abc import Callable
from dataclasses import dataclass

LOGICAL_WIDTH = 800
LOGICAL_HEIGHT = 480


@dataclass(frozen=True, slots=True)
class Rect:
    """A logical hit target with left/top-inclusive, right/bottom-exclusive edges."""

    x: int
    y: int
    width: int
    height: int

    def contains(self, point: tuple[float, float]) -> bool:
        px, py = point
        return self.x <= px < self.x + self.width and self.y <= py < self.y + self.height


def scale_point(
    point: tuple[int, int], window_size: tuple[int, int]
) -> tuple[float, float]:
    """Convert a desktop-window coordinate into the fixed logical coordinate system."""
    width, height = window_size
    if width <= 0 or height <= 0:
        raise ValueError("Window dimensions must be positive")
    return point[0] * LOGICAL_WIDTH / width, point[1] * LOGICAL_HEIGHT / height


def wrap_text(
    text: str,
    measure: Callable[[str], int],
    max_width: int,
    *,
    max_lines: int | None = None,
) -> list[str]:
    """Wrap Unicode text by measured width and visibly elide bounded overflow."""
    if max_width <= 0:
        raise ValueError("max_width must be positive")
    if max_lines is not None and max_lines <= 0:
        raise ValueError("max_lines must be positive")

    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = words.pop(0)
        while words:
            candidate = f"{current} {words[0]}"
            if measure(candidate) <= max_width:
                current = candidate
                words.pop(0)
            else:
                lines.append(current)
                current = words.pop(0)
        lines.append(current)

    bounded: list[str] = []
    for line in lines:
        if measure(line) <= max_width:
            bounded.append(line)
            continue
        chunk = ""
        for character in line:
            if chunk and measure(chunk + character) > max_width:
                bounded.append(chunk)
                chunk = character
            else:
                chunk += character
        bounded.append(chunk)
    lines = bounded

    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        suffix = "…"
        final = lines[-1]
        while final and measure(final + suffix) > max_width:
            final = final[:-1]
        lines[-1] = final.rstrip() + suffix
    return lines
