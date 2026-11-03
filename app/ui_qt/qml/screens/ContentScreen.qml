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
                title: "Practice Downloads"
                profileText: appController.activeProfileName
                networkText: appController.networkLabel
                syncText: appController.syncLabel
                isOnline: appController.isOnline
                showBack: true
                onBackClicked: appController.navigate("home")
            }

            Item {
                width: parent.width
                height: parent.height - Metrics.headerHeight

                Column {
                    anchors.fill: parent
                    anchors.margins: Spacing.md
                    spacing: Spacing.sm

                    // Storage summary card
                    AppCard {
                        width: parent.width
                        height: 68

                        Item {
                            anchors.fill: parent
                            anchors.margins: Spacing.md

                            Row {
                                anchors.left: parent.left
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: Spacing.md

                                Rectangle {
                                    width: 38; height: 38; radius: Metrics.radiusSm
                                    color: Theme.surfaceActive
                                    border.color: Theme.border
                                    border.width: 1
                                    anchors.verticalCenter: parent.verticalCenter
                                    Image {
                                        anchors.centerIn: parent
                                        width: 20; height: 20
                                        source: Assets.download
                                        fillMode: Image.PreserveAspectFit
                                    }
                                }

                                Column {
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 2

                                    Text {
                                        text: "Raspberry Pi Local Storage"
                                        color: Theme.textPrimary
                                        font.pixelSize: Typography.body
                                        font.family: Typography.fontFamily
                                        font.bold: true
                                    }

                                    Text {
                                        text: settingsController.storageUsedGb + " GB used of " + settingsController.storageTotalGb + " GB storage"
                                        color: Theme.textSecondary
                                        font.pixelSize: Typography.caption
                                        font.family: Typography.fontFamily
                                    }
                                }
                            }

                            ProgressBar {
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                width: 180
                                height: 10
                                progress: settingsController.storagePercent / 100.0
                            }
                        }
                    }

                    // Content list header
                    Text {
                        text: "Downloaded Assessment Packs"
                        color: Theme.textPrimary
                        font.pixelSize: Typography.sectionTitle
                        font.family: Typography.fontSerif
                        font.bold: true
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
                        height: parent.height - 68 - 32 - Spacing.sm * 2
                        clip: true
                        spacing: Spacing.xs
                        visible: settingsController.installedPacks.length > 0
                        model: settingsController.installedPacks

                        delegate: AppCard {
                            width: parent.width
                            height: 56
                            interactive: true
                            onClicked: {
                                libraryController.selectPack(modelData.id, modelData.version);
                            }

                            Item {
                                anchors.fill: parent
                                anchors.margins: Spacing.sm

                                Row {
                                    anchors.left: parent.left
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: Spacing.sm

                                    Rectangle {
                                        width: 36; height: 36; radius: Metrics.radiusSm
                                        color: Theme.surfaceWarm
                                        border.color: Theme.border
                                        border.width: 1
                                        anchors.verticalCenter: parent.verticalCenter
                                        Image {
                                            anchors.centerIn: parent
                                            width: 22; height: 22
                                            source: Theme.subjectIcon(modelData.subject)
                                            fillMode: Image.PreserveAspectFit
                                        }
                                    }

                                    Column {
                                        anchors.verticalCenter: parent.verticalCenter
                                        width: 440
                                        spacing: 2
                                        Text {
                                            text: modelData.title
                                            font.bold: true
                                            font.pixelSize: Typography.body
                                            font.family: Typography.fontFamily
                                            color: Theme.textPrimary
                                            elide: Text.ElideRight
                                            width: parent.width
                                        }
                                        Text {
                                            text: modelData.subject + " • " + modelData.questionCount + " questions"
                                            font.pixelSize: Typography.caption
                                            font.family: Typography.fontFamily
                                            color: Theme.textSecondary
                                        }
                                    }
                                }

                                StatusBadge {
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "Ready on Pi"
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
