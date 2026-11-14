"""Smoke tests for the current project skeleton."""

from pathlib import Path

import app
import app.main
from app.config import AppConfig
from app.input.actions import Action


def test_app_package_imports() -> None:
    from app.version import __version__ as canonical_version

    assert app.__version__ == canonical_version


def test_main_module_is_importable() -> None:
    assert callable(app.main.main)


def test_config_can_be_constructed() -> None:
    config = AppConfig()

    assert config.database_path == Path("var/assessment-device.db")
    assert config.packs_directory == Path("content")
    assert config.api_base_url is None


def test_canonical_action_enum_exists() -> None:
    assert Action.SELECT_A.value == "SELECT_A"

