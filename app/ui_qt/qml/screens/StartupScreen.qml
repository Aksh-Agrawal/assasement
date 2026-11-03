import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.canvas

    Column {
        anchors.centerIn: parent
        spacing: Spacing.lg
        width: 480

        // Device educational emblem
        Rectangle {
            width: 84
            height: 84
            radius: 42
            color: Theme.surface
            border.color: Theme.border
            border.width: 1
            anchors.horizontalCenter: parent.horizontalCenter

            Image {
                anchors.centerIn: parent
                width: 48
                height: 48
                source: Assets.raspberry
                fillMode: Image.PreserveAspectFit
            }
        }

        Column {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: Spacing.xs

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Raspberry Pi Study Buddy"
                color: Theme.deepInk
                font.pixelSize: Typography.hero
                font.bold: true
                font.family: Typography.familyEditorial
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Your dedicated offline learning companion"
                color: Theme.mutedInk
                font.pixelSize: Typography.body
                font.family: Typography.family
            }
        }

        Item { width: 1; height: Spacing.sm }

        // Two-tone paper progress rail
        ProgressBar {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 340
            height: 10
            barColor: Theme.forest
            trackColor: Theme.borderLight
            progress: appController.startupProgress
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: appController.startupStatus
            color: Theme.mutedInk
            font.pixelSize: Typography.caption
            font.family: Typography.family
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
            width: parent.width
        }
    }
}
