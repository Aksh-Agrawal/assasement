"""Shared lifetime for the Qt application used by GUI tests."""

import os

import pytest


@pytest.fixture(scope="session")
def qapp():
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQuickControls2 import QQuickStyle

    QQuickStyle.setStyle("Basic")
    app = QGuiApplication.instance() or QGuiApplication([])
    yield app


@pytest.fixture
def qt_owner(qapp):
    """Dispose Qt objects on the GUI thread even when a test fails midway."""
    from PySide6.QtCore import QCoreApplication, QEvent, QObject
    from PySide6.QtQml import QQmlApplicationEngine

    from app.ui_qt.controllers.app_controller import AppController

    owner = QObject()
    try:
        yield owner
    finally:
        try:
            # QML can still evaluate bindings during destruction.
            for engine in owner.findChildren(QQmlApplicationEngine):
                engine.deleteLater()
                QCoreApplication.sendPostedEvents(engine, QEvent.Type.DeferredDelete)
            for controller in owner.findChildren(AppController):
                controller.close()
        finally:
            owner.deleteLater()
            QCoreApplication.sendPostedEvents(owner, QEvent.Type.DeferredDelete)
