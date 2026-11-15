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
            width: 44
            height: 44
            radius: 22
            color: Theme.primaryLight
            border.color: Theme.border
            border.width: 1
            anchors.horizontalCenter: parent.horizontalCenter

            Image {
                anchors.centerIn: parent
                width: 22
                height: 22
                sourceSize: Qt.size(width, height)
                source: Assets.refresh
                fillMode: Image.PreserveAspectFit
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
