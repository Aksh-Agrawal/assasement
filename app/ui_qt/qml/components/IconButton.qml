import QtQuick 2.15
import QtQuick.Controls 2.15
import ".." 1.0

AbstractButton {
    id: root

    property url iconSource: ""
    property int buttonSize: Metrics.touchMin
    property color iconColor: Theme.deepInk
    property color backgroundColor: Theme.surface
    property color pressedColor: Theme.surfaceActive
    property color borderColor: Theme.border

    implicitWidth: Math.max(Metrics.touchMin, buttonSize)
    implicitHeight: Math.max(Metrics.touchMin, buttonSize)
    padding: 0
    focusPolicy: Qt.StrongFocus
    hoverEnabled: true
    opacity: enabled ? 1.0 : 0.5
    Accessible.name: text
    Keys.onReturnPressed: clicked()
    Keys.onEnterPressed: clicked()

    background: Rectangle {
        radius: height / 2
        color: root.down ? root.pressedColor : root.backgroundColor
        border.color: root.down || root.hovered || root.visualFocus ? Theme.forest : root.borderColor
        border.width: root.visualFocus ? Metrics.borderFocus : 1

        Rectangle {
            anchors.fill: parent
            anchors.margins: -3
            radius: height / 2
            color: "transparent"
            border.color: Theme.borderFocus
            border.width: Metrics.borderFocus
            visible: root.visualFocus
        }
    }

    contentItem: Item {
        Image {
            anchors.centerIn: parent
            width: 22
            height: 22
            sourceSize: Qt.size(width, height)
            source: root.iconSource
            fillMode: Image.PreserveAspectFit
        }
    }
}
