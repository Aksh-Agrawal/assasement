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

    height: Metrics.headerHeight
    color: "transparent"

    Row {
        anchors.left: parent.left
        anchors.leftMargin: Spacing.lg
        anchors.verticalCenter: parent.verticalCenter
        spacing: Spacing.md

        // Back button if in nested screen
        IconButton {
            visible: root.showBack
            buttonSize: 36
            iconSource: Assets.arrow_back
            onClicked: root.backClicked()
        }

        // Learner identity control / Screen Title
        Row {
            id: identity
            height: 40
            Accessible.name: "Switch Profile"
            TapHandler {
                enabled: root.allowProfileSwitch
                onTapped: root.switchProfileClicked()
            }
            spacing: Spacing.sm
            anchors.verticalCenter: parent.verticalCenter

            Rectangle {
                width: 32
                height: 32
                radius: 16
                color: Theme.primaryLight
                border.color: Theme.sage
                border.width: 1
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
                    width: Math.min(implicitWidth, root.allowProfileSwitch ? 220 : 320)
                    elide: Text.ElideRight
                    text: root.title.length > 0 ? root.title : root.profileText + (root.allowProfileSwitch ? " ▾" : "")
                    color: Theme.deepInk
                    font.pixelSize: root.title.length > 0 ? Typography.sectionTitle : Typography.body
                    font.bold: true
                    font.family: Typography.family
                }
                Text {
                    visible: root.title.length > 0 && root.profileText.length > 0
                    text: root.profileText
                    color: Theme.mutedInk
                    font.pixelSize: Typography.caption
                    font.family: Typography.family
                }
            }
        }
    }

    // Right-aligned status indicators (Calm, non-flashy)
    Row {
        anchors.right: parent.right
        anchors.rightMargin: Spacing.lg
        anchors.verticalCenter: parent.verticalCenter
        spacing: Spacing.sm

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
