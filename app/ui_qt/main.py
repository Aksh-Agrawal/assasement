"""Production entry point for the PySide6 / Qt Quick educational assessment appliance."""

import argparse
import os
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from app.auth.credentials import CredentialStore
from app.config import AppConfig
from app.diagnostics import configure_logging
from app.ui_qt.controllers.app_controller import AppController
from app.ui_qt.controllers.assessment_controller import AssessmentController
from app.ui_qt.controllers.library_controller import LibraryController
from app.ui_qt.controllers.profile_controller import ProfileController
from app.ui_qt.controllers.settings_controller import SettingsController


def parse_arguments() -> argparse.Namespace:
    config = AppConfig()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=config.database_path)
    parser.add_argument("--base-url", default=config.api_base_url)
    parser.add_argument("--fullscreen", action="store_true")
    parser.add_argument("--smoke-test", action="store_true", help="Load QML and run quick verification then exit")
    return parser.parse_args()


def run(
    database_path: Path,
    *,
    config: AppConfig | None = None,
    credentials: CredentialStore | None = None,
    fullscreen: bool = False,
    smoke_test: bool = False,
) -> int:
    config = config or AppConfig(database_path=database_path)
    credentials = credentials or CredentialStore(
        config.credential_path if database_path == config.database_path
        else database_path.parent / "device_credentials.json"
    )

    try:
        configure_logging(config.log_directory)
    except OSError:
        pass

    # Basic Qt Quick scene graph optimizations for Pi Zero 2 W
    os.environ.setdefault("QSG_RENDER_LOOP", "basic")
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

    app = QGuiApplication(sys.argv)
    app.setApplicationName("Raspberry Pi Study Buddy")
    app.setOrganizationName("Study Buddy")

    engine = QQmlApplicationEngine()

    qml_dir = Path(__file__).resolve().parent / "qml"
    engine.addImportPath(str(qml_dir))

    # Initialize controllers
    app_controller = AppController(database_path, config, credentials)
    profile_controller = ProfileController(app_controller)
    library_controller = LibraryController(app_controller)
    assessment_controller = AssessmentController(app_controller)
    settings_controller = SettingsController(app_controller)

    # Expose to QML root context
    root_context = engine.rootContext()
    root_context.setContextProperty("appController", app_controller)
    root_context.setContextProperty("profileController", profile_controller)
    root_context.setContextProperty("libraryController", library_controller)
    root_context.setContextProperty("assessmentController", assessment_controller)
    root_context.setContextProperty("settingsController", settings_controller)

    # Load main App.qml
    main_qml = qml_dir / "App.qml"
    engine.load(QUrl.fromLocalFile(str(main_qml)))

    if not engine.rootObjects():
        sys.stderr.write(f"Failed to load QML root object from {main_qml}\n")
        return 1

    root_window = engine.rootObjects()[0]

    if fullscreen:
        root_window.showFullScreen()
    else:
        root_window.show()

    if smoke_test:
        app_controller.advanceStartup()
        app_controller.close()
        return 0

    try:
        return app.exec()
    finally:
        app_controller.close()


def main() -> int:
    args = parse_arguments()
    return run(
        args.db,
        config=AppConfig(database_path=args.db, api_base_url=args.base_url),
        fullscreen=args.fullscreen,
        smoke_test=args.smoke_test,
    )


if __name__ == "__main__":
    sys.exit(main())
