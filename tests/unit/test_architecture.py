"""Lightweight import guards for architecture-sensitive modules."""

import ast
from pathlib import Path

import app

FORBIDDEN_EXTERNAL_ROOTS = {
    "RPi",
    "NetworkManager",
    "aiohttp",
    "dbus",
    "fastapi",
    "gpiozero",
    "httpx",
    "kivy",
    "pygame",
    "requests",
    "socket",
    "sqlalchemy",
    "sqlite3",
    "systemd",
    "tkinter",
    "urllib",
    "urllib3",
}


def _imports_in(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def _root(import_name: str) -> str:
    return import_name.split(".", maxsplit=1)[0]


def test_core_has_no_forbidden_or_cross_layer_imports() -> None:
    app_directory = Path(app.__file__).parent
    core_directory = app_directory / "core"

    for module_path in core_directory.glob("*.py"):
        imports = _imports_in(module_path)
        forbidden = {name for name in imports if _root(name) in FORBIDDEN_EXTERNAL_ROOTS}
        cross_layer = {
            name
            for name in imports
            if name.startswith("app.") and not name.startswith("app.core")
        }
        assert not forbidden, f"{module_path} has forbidden imports: {sorted(forbidden)}"
        assert not cross_layer, f"{module_path} crosses layer boundaries: {sorted(cross_layer)}"


def test_canonical_actions_are_platform_independent() -> None:
    app_directory = Path(app.__file__).parent
    actions_path = app_directory / "input" / "actions.py"
    imports = _imports_in(actions_path)
    forbidden = {name for name in imports if _root(name) in FORBIDDEN_EXTERNAL_ROOTS}

    assert not forbidden, f"{actions_path} has platform-dependent imports: {sorted(forbidden)}"


def test_sqlite_imports_stay_inside_data_layer() -> None:
    app_directory = Path(app.__file__).parent

    for package_name in ("core", "input", "ui"):
        for module_path in (app_directory / package_name).glob("*.py"):
            sqlite_imports = {
                name for name in _imports_in(module_path) if _root(name) == "sqlite3"
            }
            assert not sqlite_imports, (
                f"{module_path} imports sqlite3 outside app/data: {sorted(sqlite_imports)}"
            )


def test_assessment_vertical_slice_has_no_network_dependency() -> None:
    """Local orchestration may use data, but it must never require networking."""
    app_directory = Path(app.__file__).parent
    paths = [app_directory / "assessment.py", *(app_directory / "core").glob("*.py")]
    network_roots = {
        "aiohttp",
        "fastapi",
        "httpx",
        "requests",
        "socket",
        "urllib",
        "urllib3",
    }
    for module_path in paths:
        imports = _imports_in(module_path)
        forbidden = {name for name in imports if _root(name) in network_roots}
        assert not forbidden, (
            f"{module_path} has a network dependency: {sorted(forbidden)}"
        )


def test_content_pipeline_has_no_network_dependency() -> None:
    """Reusable Phase 5 validation/import remains independent from Phase 10D HTTP."""
    app_directory = Path(app.__file__).parent
    network_roots = {
        "aiohttp",
        "fastapi",
        "httpx",
        "requests",
        "socket",
        "urllib",
        "urllib3",
    }
    for filename in ("hashing.py", "validator.py", "importer.py"):
        module_path = app_directory / "content" / filename
        imports = _imports_in(module_path)
        forbidden = {name for name in imports if _root(name) in network_roots}
        assert not forbidden, (
            f"{module_path} has a network dependency: {sorted(forbidden)}"
        )


