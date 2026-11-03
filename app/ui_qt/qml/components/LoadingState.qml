import QtQuick 2.15
import ".." 1.0

Item {
    id: root

    property string message: "Preparing your study material..."

    anchors.fill: parent

    Column {
        anchors.centerIn: parent
        spacing: Spacing.md

        Rectangle {
            id: spinner
            width: 44
            height: 44
            radius: 22
            color: "transparent"
            border.color: Theme.border
            border.width: 3
            anchors.horizontalCenter: parent.horizontalCenter

            Rectangle {
                width: 10
                height: 10
                radius: 5
                color: Theme.forest
                x: parent.width / 2 - 5
                y: -5
            }

            RotationAnimation on rotation {
                from: 0
                to: 360
                duration: 1200
                loops: Animation.Infinite
                running: root.visible
            }
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.message
            color: Theme.textSecondary
            font.pixelSize: Typography.body
            font.family: Typography.fontFamily
        }
    }
}
