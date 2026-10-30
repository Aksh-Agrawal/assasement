import QtQuick 2.15
import ".." 1.0

Rectangle {
    id: root

    property string title: ""
    property string profileText: ""
    property string networkText: "Checking…"
    property string syncText: "Up to date"
    property bool isOnline: true
    property bool showBack: false
    property bool allowProfileSwitch: false
    signal switchProfileClicked()
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

        // Full identity area is a touchscreen profile control on Home.
        Row {
            id: identity
            height: 48
            Accessible.name: "Switch Profile"
            TapHandler {
                enabled: root.allowProfileSwitch
                onTapped: root.switchProfileClicked()
            }
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

            Column {
                anchors.verticalCenter: parent.verticalCenter
                Text {
                    width: Math.min(implicitWidth, root.allowProfileSwitch ? 220 : 300)
                    elide: Text.ElideRight
                    text: root.title.length > 0 ? root.title : root.profileText + (root.allowProfileSwitch ? " ▾" : "")
                    color: Theme.textPrimary
                    font.pixelSize: root.title.length > 0 ? Theme.fontSizeHeading : Theme.fontSizeBody
                    font.bold: true
                    font.family: Theme.fontFamily
                }
                Text {
                    visible: root.title.length > 0 && root.profileText.length > 0
                    text: root.profileText
                    color: Theme.textSecondary
                    font.pixelSize: Theme.fontSizeCaption
                    font.family: Theme.fontFamily
                }
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
            statusType: root.syncText.indexOf("Syncing") >= 0 ? "syncing" : (root.syncText.indexOf("Up to date") >= 0 ? "success" : "neutral")
            symbol: root.syncText.indexOf("Up to date") >= 0 ? "✓" : ""
        }
    }
}
