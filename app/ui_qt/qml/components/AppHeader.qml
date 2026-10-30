import QtQuick 2.15
import ".." 1.0

Rectangle {
    id: root

    property string title: ""
    property string profileText: ""
    property string networkText: "Online"
    property string syncText: "Synced"
    property bool isOnline: true
    property bool showBack: false
    signal backClicked()

    height: Theme.headerHeight
    color: "transparent"

    Row {
        anchors.left: parent.left
        anchors.leftMargin: 16
        anchors.verticalCenter: parent.verticalCenter
        spacing: 12

        // Back button if in nested screen
        IconButton {
            visible: root.showBack
            buttonSize: 38
            iconSource: Assets.arrow_back
            onClicked: root.backClicked()
        }

        // Student Profile pill or Title
        Row {
            spacing: 8
            anchors.verticalCenter: parent.verticalCenter

            Rectangle {
                width: 32
                height: 32
                radius: 16
                color: Theme.primaryLight
                visible: root.profileText.length > 0 && !root.showBack

                Image {
                    anchors.centerIn: parent
                    width: 18
                    height: 18
                    source: Assets.account
                    fillMode: Image.PreserveAspectFit
                }
            }

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: root.title.length > 0 ? root.title : root.profileText
                color: Theme.textPrimary
                font.pixelSize: root.title.length > 0 ? Theme.fontSizeHeading : Theme.fontSizeBody
                font.bold: true
                font.family: Theme.fontFamily
            }
        }
    }

    // Right-aligned status indicators
    Row {
        anchors.right: parent.right
        anchors.rightMargin: 16
        anchors.verticalCenter: parent.verticalCenter
        spacing: 10

        StatusBadge {
            text: root.networkText
            statusType: root.isOnline ? "online" : "offline"
        }

        StatusBadge {
            text: root.syncText
            statusType: root.syncText.indexOf("Syncing") >= 0 ? "syncing" : (root.syncText.indexOf("Synced") >= 0 ? "success" : "neutral")
            symbol: root.syncText.indexOf("Synced") >= 0 ? "✓" : ""
        }
    }
}
