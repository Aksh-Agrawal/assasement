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
        id: leading
        anchors.left: parent.left
        anchors.leftMargin: Spacing.lg
        anchors.verticalCenter: parent.verticalCenter
        width: Math.max(0, indicators.x - x - Spacing.md)
        spacing: Spacing.md

        // Back button if in nested screen
        IconButton {
            id: backButton
            visible: root.showBack
            buttonSize: 36
            iconSource: Assets.arrow_back
            onClicked: root.backClicked()
        }

        // Learner identity control / Screen Title
        Row {
            id: identity
            readonly property real textSpace: Math.max(0, leading.width
                - (backButton.visible ? backButton.width + leading.spacing : 0)
                - (profileIcon.visible ? profileIcon.width + spacing : 0)
                - (profileChevron.visible ? profileChevron.width + 4 : 0))
            height: 40
            Accessible.name: "Switch Profile"
            TapHandler {
                enabled: root.allowProfileSwitch
                onTapped: root.switchProfileClicked()
            }
            spacing: Spacing.sm
            anchors.verticalCenter: parent.verticalCenter

            Rectangle {
                id: profileIcon
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

                Row {
                    spacing: 4

                    Text {
                        width: Math.min(implicitWidth, identity.textSpace, root.allowProfileSwitch ? 220 : 320)
                        elide: Text.ElideRight
                        text: root.title.length > 0 ? root.title : root.profileText
                        color: Theme.deepInk
                        font.pixelSize: root.title.length > 0 ? Typography.sectionTitle : Typography.body
                        font.bold: true
                        font.family: Typography.family
                    }

                    Image {
                        id: profileChevron
                        visible: root.title.length === 0 && root.allowProfileSwitch
                        anchors.verticalCenter: parent.verticalCenter
                        width: 10
                        height: 10
                        source: Assets.chevron_right
                        rotation: 90
                        opacity: 0.6
                    }
                }

                Text {
                    visible: root.title.length > 0 && root.profileText.length > 0
                    width: Math.min(implicitWidth, identity.textSpace)
                    elide: Text.ElideRight
                    text: root.profileText
                    color: Theme.mutedInk
                    font.pixelSize: Typography.caption
                    font.family: Typography.family
                }
            }
        }
    }

    Column {
        id: indicators
        anchors.right: parent.right
        anchors.rightMargin: Spacing.lg
        anchors.verticalCenter: parent.verticalCenter
        spacing: Spacing.xxs

        Rectangle {
            anchors.right: parent.right
            width: statusLine.implicitWidth + 2 * Spacing.sm
            height: 20
            radius: height / 2
            color: Theme.surface
            border.color: Theme.divider

            Row {
                id: statusLine
                anchors.centerIn: parent
                spacing: Spacing.md

                Text {
                    objectName: "headerClock"
                    anchors.verticalCenter: parent.verticalCenter
                    text: appController.localDate + " · " + appController.localTime
                    color: Theme.deepInk
                    font.family: Typography.family
                    font.pixelSize: Typography.caption
                }

                Row {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: Spacing.xs

                    Image {
                        anchors.verticalCenter: parent.verticalCenter
                        width: 16
                        height: 16
                        source: Assets.battery
                    }

                    Text {
                        objectName: "headerBattery"
                        anchors.verticalCenter: parent.verticalCenter
                        text: appController.batteryLabel
                        color: Theme.deepInk
                        font.family: Typography.family
                        font.pixelSize: Typography.caption
                    }
                }

                Row {
                    id: streakStatus
                    readonly property bool glowing: appController.practiceStreak > 1
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: Spacing.xs

                    Item {
                        width: 18
                        height: 18
                        anchors.verticalCenter: parent.verticalCenter

                        Rectangle {
                            objectName: "headerStreakGlow"
                            anchors.centerIn: parent
                            width: 20
                            height: 20
                            radius: width / 2
                            color: "#40FFBB62"
                            visible: streakStatus.glowing
                        }

                        Image {
                            anchors.fill: parent
                            source: Assets.fire
                            opacity: streakStatus.glowing ? 1 : 0.42
                        }
                    }

                    Text {
                        objectName: "headerStreak"
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Streak " + (streakStatus.glowing ? appController.practiceStreak : 0)
                        color: streakStatus.glowing ? Theme.deepInk : Theme.mutedInk
                        font.family: Typography.family
                        font.pixelSize: Typography.caption
                        font.bold: streakStatus.glowing
                    }
                }
            }
        }

        Row {
            anchors.right: parent.right
            spacing: Spacing.sm

            StatusBadge {
                height: 20
                text: root.networkText
                statusType: root.isOnline ? "online" : "offline"
            }

            StatusBadge {
                height: 20
                text: root.syncText
                statusType: root.syncText.indexOf("Syncing") >= 0 ? "syncing" : (root.syncText.indexOf("Up to date") >= 0 ? "success" : "neutral")
            }
        }
    }
}
