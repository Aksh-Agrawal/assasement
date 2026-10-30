import QtQuick 2.15
import ".." 1.0

Item {
    id: root

    property string title: "Nothing here yet"
    property string description: ""
    property string actionText: ""
    property string iconSource: "../icons/info.svg"
    signal actionClicked()

    anchors.fill: parent

    Column {
        anchors.centerIn: parent
        spacing: 12
        width: Math.min(parent.width - 40, 480)

        Rectangle {
            width: 56
            height: 56
            radius: 28
            color: Theme.surfaceActive
            anchors.horizontalCenter: parent.horizontalCenter

            Image {
                anchors.centerIn: parent
                width: 28
                height: 28
                source: root.iconSource
                fillMode: Image.PreserveAspectFit
            }
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.title
            color: Theme.textPrimary
            font.pixelSize: Theme.fontSizeHeading
            font.bold: true
            font.family: Theme.fontFamily
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.description
            color: Theme.textSecondary
            font.pixelSize: Theme.fontSizeSecondary
            font.family: Theme.fontFamily
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
            width: parent.width
            visible: root.description.length > 0
        }

        Item { width: 1; height: 4 }

        PrimaryButton {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.actionText
            visible: root.actionText.length > 0
            onClicked: root.actionClicked()
        }
    }
}
