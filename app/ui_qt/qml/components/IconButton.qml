import QtQuick 2.15
import ".." 1.0

Rectangle {
    id: root

    property url iconSource: ""
    property int buttonSize: Metrics.touchMin
    property color iconColor: Theme.deepInk
    property color backgroundColor: Theme.surface
    property color pressedColor: Theme.surfaceActive
    property color borderColor: Theme.border

    signal clicked()

    implicitWidth: Math.max(Metrics.touchMin, buttonSize)
    implicitHeight: Math.max(Metrics.touchMin, buttonSize)
    radius: height / 2
    color: mouseArea.containsPress ? pressedColor : backgroundColor
    border.color: mouseArea.containsPress ? Theme.forest : borderColor
    border.width: 1
    opacity: enabled ? 1.0 : 0.5

    Image {
        anchors.centerIn: parent
        width: 22
        height: 22
        visible: root.iconSource.toString().length > 0
        source: root.iconSource
        fillMode: Image.PreserveAspectFit
        smooth: true
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        enabled: root.enabled
        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: root.clicked()
    }

    // Accessible keyboard focus indicator
    Rectangle {
        anchors.fill: parent
        anchors.margins: -3
        radius: root.radius + 3
        color: "transparent"
        border.color: Theme.borderFocus
        border.width: Metrics.borderFocus
        visible: root.activeFocus
    }
}
