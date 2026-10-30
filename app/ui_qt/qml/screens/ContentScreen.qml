import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.background

    Row {
        anchors.fill: parent

        NavRail {
            id: rail
            height: parent.height
            currentTab: "practice"
            onTabSelected: function(tab) {
                if (tab === "home") appController.navigate("home");
                else if (tab === "library") appController.navigate("subjects");
                else if (tab === "practice") appController.navigate("content");
                else if (tab === "history") appController.navigate("history");
                else if (tab === "settings") appController.navigate("settings");
            }
        }

        Column {
            width: parent.width - rail.width
            height: parent.height

            AppHeader {
                width: parent.width
                title: "Practice & Downloads"
                networkText: appController.networkLabel
                syncText: appController.syncLabel
                isOnline: appController.isOnline
                showBack: true
                onBackClicked: appController.navigate("home")
            }

            Item {
                width: parent.width
                height: parent.height - Theme.headerHeight

                Column {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 12

                    // Storage summary card
                    AppCard {
                        width: parent.width
                        height: 74

                        Row {
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 16

                            Rectangle {
                                width: 44; height: 44; radius: 12
                                color: Theme.primaryLight
                                Image { anchors.centerIn: parent; width: 24; height: 24; source: "../icons/download.svg" }
                            }

                            Column {
                                width: parent.width - 44 - 16 - 220
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 4

                                Text {
                                    text: "Raspberry Pi Local Storage"
                                    color: Theme.textPrimary
                                    font.pixelSize: 15
                                    font.bold: true
                                }

                                Text {
                                    text: settingsController.storageUsedGb + " GB used of " + settingsController.storageTotalGb + " GB total"
                                    color: Theme.textSecondary
                                    font.pixelSize: 13
                                }
                            }

                            ProgressBar {
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                width: 180
                                height: 12
                                progress: settingsController.storagePercent / 100.0
                            }
                        }
                    }

                    // Content list header
                    Text {
                        text: "Downloaded Assessment Packs"
                        color: Theme.textPrimary
                        font.pixelSize: Theme.fontSizeHeading
                        font.bold: true
                        font.family: Theme.fontFamily
                    }

                    // Installed packs list
                    EmptyState {
                        anchors.centerIn: parent
                        visible: settingsController.installedPacks.length === 0
                        title: "No Practice Packs Downloaded"
                        description: "Connect to Wi-Fi to download packs, or explore available subjects in the library."
                        actionText: "Browse Library"
                        onActionClicked: appController.navigate("subjects")
                    }

                    ListView {
                        width: parent.width
                        height: parent.height - 74 - 40 - 24
                        clip: true
                        spacing: 8
                        visible: settingsController.installedPacks.length > 0
                        model: settingsController.installedPacks

                        delegate: AppCard {
                            width: parent.width
                            height: 60
                            interactive: true
                            onClicked: {
                                libraryController.selectPack(modelData.id, modelData.version);
                            }

                            Row {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 12

                                Rectangle {
                                    width: 36; height: 36; radius: 8
                                    color: Theme.surfaceActive
                                    Image { anchors.centerIn: parent; width: 20; height: 20; source: "../icons/practice.svg" }
                                }

                                Column {
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: parent.width - 36 - 12 - 160
                                    spacing: 2
                                    Text { text: modelData.title; font.bold: true; font.pixelSize: 15; color: Theme.textPrimary; elide: Text.ElideRight }
                                    Text { text: modelData.subject + " • " + modelData.questionCount + " questions"; font.pixelSize: 12; color: Theme.textSecondary }
                                }

                                StatusBadge {
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "Ready on this device"
                                    statusType: "success"
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
