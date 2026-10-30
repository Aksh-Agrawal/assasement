import QtQuick 2.15
import ".." 1.0

Item {
    id: root

    property string message: "Loading..."

    anchors.fill: parent

    Column {
        anchors.centerIn: parent
        spacing: 16

        Rectangle {
            id: spinner
            width: 44
            height: 44
            radius: 22
            color: "transparent"
            border.color: Theme.primary
            border.width: 3
            anchors.horizontalCenter: parent.horizontalCenter

            Rectangle {
                width: 10
                height: 10
                radius: 5
                color: Theme.highlight
                x: parent.width / 2 - 5
                y: -5
            }

            RotationAnimation on rotation {
                from: 0
                to: 360
                duration: 1000
                loops: Animation.Infinite
                running: root.visible
            }
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.message
            color: Theme.textSecondary
            font.pixelSize: Theme.fontSizeBody
            font.family: Theme.fontFamily
        }
    }
}
