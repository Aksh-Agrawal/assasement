"""Pygame Phase 7A desktop entry point over the framework-neutral UI controller."""

import argparse
import traceback
from pathlib import Path

import pygame

from app.config import AppConfig
from app.data.repo import Repository
from app.diagnostics import configure_logging
from app.input.actions import Action
from app.input.keyboard import KeyboardInput
from app.ui.controller import UIController, UIScreen
from app.ui.layout import LOGICAL_HEIGHT, LOGICAL_WIDTH, scale_point
from app.ui.screens import (
    confidence,
    detail,
    error,
    home,
    question,
    question_set,
    result,
    review,
    subject,
    submit,
)
from app.ui.screens.common import Control, make_fonts
from app.ui.theme import THEME

SCREEN_RENDERERS = {
    UIScreen.HOME: home.render,
    UIScreen.SUBJECT: subject.render,
    UIScreen.QUESTION_SET: question_set.render,
    UIScreen.QUESTION: question.render,
    UIScreen.QUESTION_DETAIL: detail.render,
    UIScreen.CONFIDENCE: confidence.render,
    UIScreen.SUBMIT_CONFIRM: submit.render,
    UIScreen.RESULT: result.render,
    UIScreen.REVIEW: review.render,
    UIScreen.ERROR: error.render,
}


def _arguments() -> argparse.Namespace:
    config = AppConfig()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=config.database_path)
    return parser.parse_args()


def _save_screenshot(surface: pygame.Surface) -> Path:
    output = Path("var/screenshots")
    output.mkdir(parents=True, exist_ok=True)
    existing = sorted(output.glob("phase8a-*.png"))
    path = output / f"phase8a-{len(existing) + 1:03d}.png"
    pygame.image.save(surface, path)
    return path


def _clicked_control(
    controls: list[Control], point: tuple[int, int], window_size: tuple[int, int]
) -> Control | None:
    logical = scale_point(point, window_size)
    return next((control for control in reversed(controls) if control.rect.contains(logical)), None)


def _show_startup_error(
    message: str,
    window: pygame.Surface,
    logical_surface: pygame.Surface,
    fonts,
) -> None:
    """Keep database/startup failures in a readable normal UI instead of a traceback view."""
    keyboard = KeyboardInput()
    clock = pygame.time.Clock()
    running = True
    while running:
        logical_surface.fill(THEME.background)
        controls = error.render_message(logical_surface, message, fonts)
        window.blit(pygame.transform.smoothscale(logical_surface, window.get_size()), (0, 0))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                action = keyboard.translate(pygame.key.name(event.key))
                if action is Action.BACK:
                    running = False
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                control = _clicked_control(controls, event.pos, window.get_size())
                if control is not None:
                    running = False
        clock.tick(30)


def run(database_path: Path) -> int:
    configure_logging(AppConfig().log_directory)
    pygame.init()
    pygame.display.set_caption("Offline Assessment — Phase 8A")
    window = pygame.display.set_mode((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.RESIZABLE)
    logical_surface = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT))
    fonts = make_fonts()
    keyboard = KeyboardInput()
    clock = pygame.time.Clock()

    try:
        repository = Repository(database_path)
    except Exception as startup_error:
        traceback.print_exc()
        _show_startup_error(str(startup_error), window, logical_surface, fonts)
        pygame.quit()
        return 1

    try:
        controller = UIController(repository)
    except Exception as startup_error:
        traceback.print_exc()
        repository.close()
        _show_startup_error(str(startup_error), window, logical_surface, fonts)
        pygame.quit()
        return 1
    running = True
    try:
        while running:
            logical_surface.fill(THEME.background)
            controls = SCREEN_RENDERERS[controller.screen](logical_surface, controller, fonts)
            window.blit(pygame.transform.smoothscale(logical_surface, window.get_size()), (0, 0))
            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F12:
                        path = _save_screenshot(logical_surface)
                        print(f"Screenshot saved: {path}")
                    else:
                        action = keyboard.translate(pygame.key.name(event.key))
                        if action is not None:
                            controller.handle(action)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    control = _clicked_control(controls, event.pos, window.get_size())
                    if control is not None:
                        controller.handle(control.action)
            clock.tick(30)
    finally:
        try:
            controller.close()
        finally:
            repository.close()
            pygame.quit()
    return 0


def main() -> int:
    return run(_arguments().db)


if __name__ == "__main__":
    raise SystemExit(main())
