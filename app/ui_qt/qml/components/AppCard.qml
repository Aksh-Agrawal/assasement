import QtQuick 2.15
import ".." 1.0

Rectangle {
    id: root

    property bool interactive: false
    property bool selected: false
    property bool highlighted: false
    signal clicked()

    color: selected ? Theme.surfaceSelected : (highlighted ? Theme.surfaceActive : Theme.surface)
    radius: Theme.cardRadius
    border.color: selected ? Theme.primary : (interactive && mouseArea.containsPress ? Theme.primaryDark : Theme.border)
    border.width: selected ? 2 : 1

    Behavior on color {
        ColorAnimation { duration: Theme.animDuration }
    }

    Behavior on border.color {
        ColorAnimation { duration: Theme.animDuration }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        enabled: root.interactive
        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: root.clicked()
    }
}
