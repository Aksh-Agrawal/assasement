import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.background

    Column {
        anchors.centerIn: parent
        spacing: 16
        width: 480

        // Device educational mark
        Rectangle {
            width: 76
            height: 76
            radius: 38
            color: Theme.surface
            border.color: Theme.border
            border.width: 1
            anchors.horizontalCenter: parent.horizontalCenter

            Image {
                anchors.centerIn: parent
                width: 44
                height: 44
                source: Assets.raspberry
                fillMode: Image.PreserveAspectFit
            }
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Raspberry Pi Study Buddy"
            color: Theme.textPrimary
            font.pixelSize: Theme.fontSizeTitle
            font.bold: true
            font.family: Theme.fontFamily
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "A brighter tomorrow through practice"
            color: Theme.textSecondary
            font.pixelSize: Theme.fontSizeSecondary
            font.family: Theme.fontFamily
        }

        Item { width: 1; height: 12 }

        ProgressBar {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 360
            height: 14
            progress: appController.startupProgress
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: appController.startupStatus
            color: Theme.textSecondary
            font.pixelSize: Theme.fontSizeCaption
            font.family: Theme.fontFamily
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
            width: parent.width
        }
    }
}
