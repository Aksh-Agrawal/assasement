"""Render reproducible UI previews using a temporary real SQLite assessment.

This never opens the student's database. Preview data is explicitly seeded from
the repository sample pack; scores are produced by the assessment application.
"""

import argparse
import json
import os
import tempfile
from pathlib import Path
from uuid import uuid4

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from app.auth.credentials import CredentialStore
from app.config import AppConfig
from app.content.importer import import_pack
from app.core.models import Profile
from app.data.repo import Repository
from app.input.actions import Action
from app.ui.controller import UIController
from app.ui.device import DeviceConsole
from app.ui.router import SETTINGS_ROUTES, UIScreen
from app.ui.screens import console, startup
from app.ui.screens.common import make_fonts
from app.ui.startup import StartupSession
from app.ui.theme import THEME


def previews(output):
    output.mkdir(parents=True, exist_ok=True)
    pygame.font.init()
    surface, fonts = pygame.Surface((800, 480)), make_fonts()
    images = []

    def capture(name, callback):
        surface.fill(THEME.background)
        callback()
        pygame.image.save(surface, output / f"{name}.png")
        pygame.image.save(pygame.transform.scale(surface, (800, 600)),
                          output / f"{name}-800x600.png")
        images.append((name, surface.copy()))

    def choose(c, command, value=None):
        index = next(
            i
            for i, choice in enumerate(c.choices)
            if choice.command == command and (value is None or choice.value == value)
        )
        c.handle(Action.CONFIRM, ("choice", index))

    with tempfile.TemporaryDirectory(prefix="assessment-ui-preview-") as temporary:
        root = Path(temporary)
        path = root / "preview.db"
        config = AppConfig(
            database_path=path, log_directory=root / "logs", update_root=root / "updates"
        )
        session = StartupSession(path, config, CredentialStore(root / "credentials.json"))
        while not session.complete and not session.failed:
            session.advance()
        capture("startup", lambda: startup.render(surface, session, fonts))
        session.close()
        with Repository(path) as repo:
            import_pack(Path("content/sample_biology.json"), repo, make_active=True)
            account = str(uuid4())
            repo.create_profile(Profile(id="preview-student", display_name="Demo student",
                                        cloud_account_id=account, cloud_profile_id=str(uuid4()),
                                        ownership_state="owned"))
            repo.cache_student_account_context(account, "Demo account")
            cached = {"profile_count": 1, "profiles": [{"local_profile_id": "preview-student"}]}
            repo.set_setting("account_profiles", json.dumps(cached))
            device = DeviceConsole(path, config)
            c = UIController(repo, startup=True, device=device)
            c.finish_splash()

            def snap(name):
                capture(name, lambda: console.render(surface, c, fonts))

            snap("profile")
            choose(c, "profile", 0)
            snap("home")
            choose(c, "route", UIScreen.SUBJECTS)
            snap("subjects")
            choose(c, "subject", 0)
            snap("chapters")
            choose(c, "chapter", 0)
            snap("packs")
            choose(c, "pack", 0)
            snap("test_setup")
            choose(c, "start")
            snap("question")
            c.handle(Action.CONFIRM)
            snap("full_text")
            c.handle(Action.BACK)
            c.handle(Action.SELECT_A)
            snap("confidence")
            c.handle(Action.SURE)
            c.handle(Action.MENU)
            snap("assessment_menu")
            choose(c, "route", UIScreen.LEAVE_CONFIRM)
            snap("leave_confirm")
            c.handle(Action.BACK)
            c.handle(Action.MENU)
            choose(c, "navigator")
            snap("navigator")
            c.handle(Action.BACK)
            for index in range(20):
                c.application.go_to_question(index)
                c.handle(Action.SELECT_A)
                c.handle((Action.SURE, Action.NOT_SURE, Action.GUESSING)[index % 3])
            c.handle(Action.SUBMIT)
            snap("submit_confirm")
            c.handle(Action.SUBMIT)
            snap("result")
            choose(c, "review", "all")
            snap("review")
            c.handle(Action.BACK)
            choose(c, "done")
            choose(c, "route", UIScreen.PROGRESS)
            snap("progress")
            c.handle(Action.BACK)
            choose(c, "route", UIScreen.SETTINGS)
            snap("settings")
            for route in SETTINGS_ROUTES:
                choose(c, "route", route)
                if route is UIScreen.DIAGNOSTICS:
                    device.diagnostics = device._execute("diagnostics")
                snap(route.name.lower())
                c.handle(Action.BACK)
            c.route(UIScreen.PROFILE)
            choose(c, "route", UIScreen.ADD_PROFILE)
            snap("add_profile")
            c.handle(Action.BACK)
            c.route(UIScreen.PAIRING)
            snap("pairing")
            c.handle(Action.BACK)
            repo.create_profile(
                Profile(id="protected-preview", display_name="Protected student",
                        cloud_account_id=account, cloud_profile_id=str(uuid4()), ownership_state="owned"),
                pin_hash="opaque-existing-format",
                pin_salt="preview-salt",
            )
            cached["profiles"].append({"local_profile_id": "protected-preview"})
            repo.set_setting("account_profiles", json.dumps(cached))
            c.refresh_catalog()
            choose(c, "profile", 1)
            snap("pin")
            c.close()
        from app.ui.screens import recovery

        corrupt = root / "corrupt.db"
        corrupt.write_bytes(b"Unusable database for recovery preview")
        failed = StartupSession(corrupt, config, CredentialStore(root / "credentials.json"))
        while not failed.failed and not failed.complete:
            failed.advance()
        capture("recovery", lambda: recovery.render(surface, failed, fonts))
        failed.close()
    columns, cell_width, cell_height = 3, 400, 264
    sheet = pygame.Surface(
        (columns * cell_width, ((len(images) + columns - 1) // columns) * cell_height)
    )
    sheet.fill(THEME.background)
    for index, (name, image) in enumerate(images):
        x, y = index % columns * cell_width, index // columns * cell_height
        sheet.blit(
            fonts.small.render(name.replace("_", " ").upper(), True, THEME.foreground),
            (x + 8, y + 4),
        )
        sheet.blit(pygame.transform.smoothscale(image, (400, 240)), (x, y + 24))
    pygame.image.save(sheet, output / "contact-sheet.png")
    pygame.quit()
    return len(images)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/ui-redesign"))
    args = parser.parse_args()
    print(f"Rendered {previews(args.output)} actual device screens to {args.output}")


if __name__ == "__main__":
    main()
