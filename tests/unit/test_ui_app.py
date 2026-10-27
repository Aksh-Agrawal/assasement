"""Window-independent checks for pygame development helpers."""

from pathlib import Path

import pygame

from app.ui.app import _save_screenshot


def test_screenshot_helper_writes_numbered_png(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    surface = pygame.Surface((40, 30))
    first = _save_screenshot(surface)
    second = _save_screenshot(surface)
    assert first == Path("var/screenshots/phase8a-001.png")
    assert second == Path("var/screenshots/phase8a-002.png")
    assert first.is_file()
    assert second.is_file()
