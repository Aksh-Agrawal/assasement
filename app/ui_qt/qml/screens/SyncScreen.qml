import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.canvas

    AppHeader {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        title: "Sync"
        networkText: appController.networkLabel
        syncText: appController.syncLabel
        isOnline: appController.isOnline
        showBack: true
        onBackClicked: appController.navigate("settings")
    }

    Item {
        anchors.top: header.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: Spacing.lg

        AppCard {
            anchors.centerIn: parent
            width: 520
            implicitHeight: contentCol.implicitHeight + 48

            Column {
                id: contentCol
                anchors.centerIn: parent
                width: parent.width - 48
                spacing: Spacing.md

                // Sync Emblem
                Rectangle {
                    width: 60
                    height: 60
                    radius: 30
                    color: settingsController.isSyncing ? Theme.primaryLight : Theme.surfaceSelected
                    border.color: Theme.sage
                    border.width: 1
                    anchors.horizontalCenter: parent.horizontalCenter

                    Image {
                        anchors.centerIn: parent
                        width: 30
                        height: 30
                        source: Assets.sync
                        fillMode: Image.PreserveAspectFit
                    }
                }

                // Student-Facing Status & Headline
                Column {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 4

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: settingsController.syncStatusSummary
                        color: Theme.deepInk
                        font.pixelSize: Typography.pageTitle
                        font.bold: true
                        font.family: Typography.familyEditorial
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Last synchronized: " + (settingsController.lastSyncTime || "Just now")
                        color: Theme.mutedInk
                        font.pixelSize: Typography.body
                        font.family: Typography.family
                    }
                }

                Rectangle { width: parent.width; height: 1; color: Theme.borderLight }

                // Automatic Sync Toggle Row
                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: Spacing.lg

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Automatic Cloud Sync"
                        color: Theme.deepInk
                        font.pixelSize: Typography.body
                        font.bold: true
                        font.family: Typography.family
                    }

                    Rectangle {
                        anchors.verticalCenter: parent.verticalCenter
                        width: 76
                        height: 34
                        radius: 17
                        color: settingsController.automaticSync ? Theme.forest : Theme.surfaceActive
                        border.color: settingsController.automaticSync ? Theme.primaryDark : Theme.border
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: settingsController.automaticSync ? "ON" : "OFF"
                            color: settingsController.automaticSync ? Theme.textOnPrimary : Theme.mutedInk
                            font.pixelSize: Typography.caption
                            font.bold: true
                            font.family: Typography.family
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: settingsController.setAutomaticSync(!settingsController.automaticSync)
                        }
                    }
                }

                Item { width: 1; height: Spacing.xs }

                // Primary Sync Now Action
                PrimaryButton {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 220
                    preferredHeight: Metrics.touchNormal
                    buttonColor: Theme.forest
                    text: settingsController.isSyncing ? "Syncing Now…" : "Sync Now"
                    enabled: !settingsController.isSyncing
                    iconSource: Assets.sync
                    onClicked: settingsController.startSync()
                }
            }
        }
    }
}
