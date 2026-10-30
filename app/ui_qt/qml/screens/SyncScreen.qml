import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.background

    AppHeader {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        title: "Sync Management"
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
        anchors.margins: 16

        AppCard {
            anchors.centerIn: parent
            width: 580
            implicitHeight: contentCol.implicitHeight + 40

            Column {
                id: contentCol
                anchors.centerIn: parent
                width: parent.width - 48
                spacing: 16

                // Status Icon & Title
                Row {
                    spacing: 14
                    anchors.horizontalCenter: parent.horizontalCenter

                    Rectangle {
                        width: 50
                        height: 50
                        radius: 25
                        color: settingsController.pendingAttemptsCount > 0 ? "#FFF3E0" : "#E8F5E9"

                        Image {
                            anchors.centerIn: parent
                            width: 26
                            height: 26
                            source: "../icons/sync.svg"
                            fillMode: Image.PreserveAspectFit
                        }
                    }

                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 2

                        Text {
                            text: settingsController.pendingAttemptsCount > 0
                                ? settingsController.pendingAttemptsCount + " Assessments Waiting to Sync"
                                : "All Progress Up to Date!"
                            color: Theme.textPrimary
                            font.pixelSize: Theme.fontSizeHeading
                            font.bold: true
                            font.family: Theme.fontFamily
                        }

                        Text {
                            text: "Your learning data is safely stored locally on this Raspberry Pi."
                            color: Theme.textSecondary
                            font.pixelSize: Theme.fontSizeCaption
                        }
                    }
                }

                Rectangle { width: parent.width; height: 1; color: Theme.divider }

                // Sync details grid
                Grid {
                    width: parent.width
                    columns: 2
                    rowSpacing: 12
                    columnSpacing: 20

                    Column {
                        spacing: 2
                        Text { text: "Cloud Status"; color: Theme.textSecondary; font.pixelSize: 13 }
                        StatusBadge {
                            text: settingsController.cloudStatus
                            statusType: settingsController.cloudStatus === "Ready" || settingsController.cloudStatus === "Available" ? "success" : "neutral"
                        }
                    }

                    Column {
                        spacing: 2
                        Text { text: "Last Synchronized"; color: Theme.textSecondary; font.pixelSize: 13 }
                        Text { text: settingsController.lastSyncTime; color: Theme.textPrimary; font.bold: true; font.pixelSize: 15 }
                    }

                    Column {
                        spacing: 2
                        Text { text: "Pending Completed Attempts"; color: Theme.textSecondary; font.pixelSize: 13 }
                        Text { text: settingsController.pendingAttemptsCount + " attempt(s)"; color: Theme.textPrimary; font.bold: true; font.pixelSize: 15 }
                    }

                    Column {
                        spacing: 2
                        Text { text: "Sync Policy"; color: Theme.textSecondary; font.pixelSize: 13 }
                        Text { text: "Automatic on Wi-Fi"; color: Theme.textPrimary; font.bold: true; font.pixelSize: 15 }
                    }
                }

                Item { width: 1; height: 6 }

                PrimaryButton {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 240
                    preferredHeight: Theme.touchNormal
                    text: settingsController.isSyncing ? "Syncing Now…" : "Sync Now"
                    enabled: !settingsController.isSyncing
                    iconSource: "../icons/sync.svg"
                    onClicked: settingsController.startSync()
                }
            }
        }
    }
}
