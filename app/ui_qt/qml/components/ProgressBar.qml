import QtQuick 2.15
import ".." 1.0

Rectangle {
    id: root

    property real progress: 0.0 // 0.0 to 1.0
    property color barColor: Theme.primary
    property color trackColor: Theme.border

    implicitHeight: 12
    implicitWidth: 200
    radius: height / 2
    color: trackColor
    clip: true

    Rectangle {
        id: fillRect
        height: parent.height
        width: Math.max(0, Math.min(parent.width, parent.width * root.progress))
        radius: root.radius
        color: root.barColor

        Behavior on width {
            NumberAnimation { duration: Theme.animDuration; easing.type: Easing.OutQuad }
        }
    }
}
