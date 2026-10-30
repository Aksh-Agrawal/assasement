import QtQuick 2.15
import ".." 1.0

Rectangle {
    id: root

    property string iconSource: ""
    property int buttonSize: Theme.touchMin
    property color iconColor: Theme.textPrimary
    property color backgroundColor: Theme.surface
    property color pressedColor: Theme.surfaceActive

    signal clicked()

    implicitWidth: buttonSize
    implicitHeight: buttonSize
    radius: buttonSize / 2
    color: mouseArea.containsPress ? pressedColor : backgroundColor
    border.color: Theme.border
    border.width: 1
    opacity: enabled ? 1.0 : 0.5

    Image {
        anchors.centerIn: parent
        width: root.buttonSize * 0.48
        height: root.buttonSize * 0.48
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
}
