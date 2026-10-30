"""Portable, exact-case asset contract and actual QML URL/image loading."""

import os
import re
from pathlib import Path, PurePosixPath

import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QSG_RENDER_LOOP"] = "basic"

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

QML = Path(__file__).resolve().parents[1] / "app/ui_qt/qml"
DECLARATION = re.compile(
    r'readonly property url (\w+): Qt.resolvedUrl\("([^"\n]+)"\)'
)


def exact_asset(root, relative):
    """Check each directory entry explicitly, even on case-insensitive Windows."""
    path = PurePosixPath(relative)
    assert not path.is_absolute() and ".." not in path.parts and ":" not in relative
    current = root
    for part in path.parts:
        assert part in {entry.name for entry in current.iterdir()}, relative
        current = current / part
    assert current.is_file(), relative
    return current


def test_asset_manifest_is_complete_and_exact_case():
    declarations = DECLARATION.findall((QML / "Assets.qml").read_text(encoding="utf-8"))
    assert declarations
    assert len({name for name, _ in declarations}) == len(declarations)
    assert {path for _, path in declarations} == {
        "icons/" + path.name for path in (QML / "icons").glob("*.svg")
    }
    for _, relative in declarations:
        exact_asset(QML, relative)


@pytest.mark.parametrize("relative", ["icons/Home.svg", "icons/missing.svg", "Icons/home.svg"])
def test_case_and_missing_file_guard_rejects_bad_assets(relative):
    with pytest.raises(AssertionError):
        exact_asset(QML, relative)


def test_qml_resolves_and_loads_every_declared_asset():
    app = QGuiApplication.instance() or QGuiApplication([])
    engine = QQmlEngine()
    declarations = DECLARATION.findall((QML / "Assets.qml").read_text(encoding="utf-8"))
    probe = QQmlComponent(engine)
    fields = "\n".join(f"property url {name}: Assets.{name}" for name, _ in declarations)
    probe.setData(('import QtQuick 2.15\nimport "." 1.0\nQtObject {\n' + fields + '\n}').encode(),
                  QUrl.fromLocalFile(str(QML / "AssetProbe.qml")))
    obj = probe.create()
    assert obj is not None, [error.toString() for error in probe.errors()]
    image_component = QQmlComponent(engine)
    image_component.setData(b"import QtQuick 2.15; Image { property bool loaded: status === Image.Ready }",
                            QUrl.fromLocalFile(str(QML / "ImageProbe.qml")))
    images = []
    for name, relative in declarations:
        url = obj.property(name)
        assert url.isLocalFile(), name
        assert Path(url.toLocalFile()) == exact_asset(QML, relative)
        image = image_component.createWithInitialProperties({"source": url, "asynchronous": False})
        assert image is not None
        images.append(image)
        app.processEvents()
        assert image.property("loaded"), f"{name}: {url.toString()}"


def test_only_assets_singleton_owns_asset_paths():
    names = {name for name, _ in DECLARATION.findall((QML / "Assets.qml").read_text(encoding="utf-8"))}
    for path in QML.rglob("*.qml"):
        if path.name == "Assets.qml":
            continue
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[\"'](?:\.\./)*icons/", text), path
        assert not re.search(r"[\"'][^\"'\n]*\.(?:svg|png|jpg|ttf|woff)[\"']", text), path
        assert not re.search(r"property\s+string\s+iconSource", text), path
        assert set(re.findall(r"Assets\.(\w+)", text)) <= names, path
