"""Generate app/ui_qt/qml/Assets.qml conforming strictly to tests/test_qml_assets.py contract."""

from pathlib import Path

QML = Path("app/ui_qt/qml")
ICONS = QML / "icons"

icon_paths = sorted(list(ICONS.glob("*.svg")))
print(f"Found {len(icon_paths)} icons in {ICONS}")

lines = [
    "pragma Singleton",
    "import QtQuick 2.15",
    "",
    "QtObject {",
    "    id: assets",
    "",
]

for p in icon_paths:
    name = p.stem
    rel = f"icons/{p.name}"
    lines.append(f'    readonly property url {name}: Qt.resolvedUrl("{rel}")')

lines.append("}\n")

output_path = QML / "Assets.qml"
output_path.write_text("\n".join(lines), encoding="utf-8")
print(f"Wrote {len(icon_paths)} asset declarations to {output_path}")
