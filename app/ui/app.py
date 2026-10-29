"""Pygame entry point for the offline-first student assessment device."""

import argparse
from pathlib import Path

import pygame

from app.config import AppConfig
from app.diagnostics import configure_logging
from app.input.actions import Action
from app.ui.controller import UIController, UIScreen
from app.ui.layout import LOGICAL_HEIGHT, LOGICAL_WIDTH, scale_point
from app.ui.screens.common import Control, make_fonts
from app.ui.theme import THEME


def _arguments() -> argparse.Namespace:
    config = AppConfig()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=config.database_path)
    parser.add_argument("--base-url", default=config.api_base_url)
    parser.add_argument("--fullscreen", action="store_true")
    parser.add_argument("--gpio", action="store_true")
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


def run(
    database_path: Path,
    *,
    config=None,
    credentials=None,
    fullscreen=False,
    gpio=False,
    max_frames=None,
) -> int:
    """One boot-to-app entry point; local startup and GUI need no network."""
    import logging
    import time

    from app.auth.credentials import CredentialStore
    from app.input.buttons import ButtonHardwareUnavailable, ButtonInput
    from app.input.ui import keyboard_input
    from app.ui.device import DeviceConsole
    from app.ui.screens import console, recovery, startup
    from app.ui.startup import StartupSession

    config = config or AppConfig(database_path=database_path)
    credentials = credentials or CredentialStore(
        config.credential_path if database_path == config.database_path
        else database_path.parent / "device_credentials.json"
    )
    try:
        configure_logging(config.log_directory)
    except OSError:
        # Logging storage is optional; a usable local database is the boot gate.
        pass
    pygame.init()
    pygame.display.set_caption("Assessment Device")
    flags = pygame.FULLSCREEN if fullscreen else pygame.RESIZABLE
    window = pygame.display.set_mode((LOGICAL_WIDTH, LOGICAL_HEIGHT), flags)
    logical_surface = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT))
    fonts = make_fonts()
    clock = pygame.time.Clock()
    session = StartupSession(database_path, config, credentials)
    controller = None
    controls = []
    recovery_mode = "recovery"
    running, dirty, frame = True, True, 0
    last_timer_second = -1
    input_event = pygame.event.custom_type()
    buttons = ButtonInput(
        lambda action: pygame.event.post(pygame.event.Event(input_event, action=action))
    )
    if gpio:
        try:
            buttons.start()
        except ButtonHardwareUnavailable:
            logging.getLogger(__name__).warning(
                "GPIO unavailable; keyboard and touch remain available"
            )
    try:
        while running:
            if dirty:
                logical_surface.fill(THEME.background)
                if controller:
                    controls = console.render(logical_surface, controller, fonts)
                elif session.failed:
                    controls = recovery.render(logical_surface, session, fonts, mode=recovery_mode)
                else:
                    controls = startup.render(logical_surface, session, fonts)
                window.blit(pygame.transform.scale(logical_surface, window.get_size()), (0, 0))
                pygame.display.flip()
                dirty = False

            for event in pygame.event.get():
                action, payload = None, None
                if event.type == pygame.QUIT:
                    running = False
                elif event.type in {pygame.VIDEORESIZE, pygame.WINDOWEXPOSED}:
                    dirty = True
                elif event.type == input_event:
                    action = event.action
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F12:
                        _save_screenshot(logical_surface)
                    else:
                        entry = bool(
                            controller
                            and (
                                controller.screen in {UIScreen.PIN, UIScreen.ADD_PROFILE, UIScreen.LINK_PROFILE}
                                or controller.screen is UIScreen.WIFI
                                and controller.selected_wifi
                            )
                        )
                        message = keyboard_input(
                            pygame.key.name(event.key), character=event.unicode, text_entry=entry
                        )
                        if message:
                            action, payload = message.action, message.payload
                elif (
                    event.type == pygame.MOUSEBUTTONUP
                    and event.button == 1
                    and not getattr(event, "touch", False)
                ):
                    control = _clicked_control(controls, event.pos, window.get_size())
                    if control:
                        action, payload = control.action, control.payload
                elif event.type == pygame.FINGERUP:
                    point = (
                        round(event.x * window.get_width()),
                        round(event.y * window.get_height()),
                    )
                    control = _clicked_control(controls, point, window.get_size())
                    if control:
                        action, payload = control.action, control.payload
                elif event.type == pygame.MOUSEWHEEL and controller:
                    step = 80 if controller.screen is UIScreen.QUESTION else 3
                    action, payload = Action.CONFIRM, ("scroll", -event.y * step)
                if action:
                    if controller:
                        controller.handle(action, payload)
                    elif session.failed:
                        command = (
                            payload[1]
                            if payload
                            else {
                                Action.CONFIRM: "retry",
                                Action.SELECT_A: "retry",
                                Action.SELECT_B: "diagnostics",
                                Action.SELECT_C: "options",
                                Action.BACK: "exit",
                            }.get(action)
                        )
                        if command == "retry":
                            session.close()
                            session = StartupSession(database_path, config, credentials)
                            recovery_mode = "recovery"
                        elif command == "exit":
                            running = False
                        elif command in {"diagnostics", "options"}:
                            recovery_mode = command
                    dirty = True
            if not controller and not session.failed:
                session.advance()
                dirty = True
                if session.complete:
                    try:
                        device = DeviceConsole(database_path, config, credentials)
                        controller = UIController(session.repository, startup=True, device=device)
                        controller.startup_rows = tuple(session.rows)
                        controller.finish_splash()
                        if controller.screen is UIScreen.RECOVERY:
                            raise RuntimeError("Local safety check failed")
                    except Exception:
                        logging.getLogger(__name__).error(
                            "Local UI startup failed; recovery available"
                        )
                        controller = None
                        session.failed = True
            if controller:
                dirty = controller.tick() or dirty
                second = int(time.monotonic())
                if controller.screen is UIScreen.QUESTION and second != last_timer_second:
                    last_timer_second = second
                    dirty = True
            frame += 1
            if max_frames is not None and frame >= max_frames:
                running = False
            clock.tick(30)
    finally:
        try:
            if controller:
                controller.close()
        finally:
            buttons.close()
            session.close()
            pygame.quit()
    return 1 if session.failed else 0


def main() -> int:
    args = _arguments()
    return run(
        args.db,
        config=AppConfig(database_path=args.db, api_base_url=args.base_url),
        fullscreen=args.fullscreen,
        gpio=args.gpio,
    )


if __name__ == "__main__":
    raise SystemExit(main())
