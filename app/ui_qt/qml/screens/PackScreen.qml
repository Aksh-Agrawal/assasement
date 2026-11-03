import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.canvas

    Row {
        anchors.fill: parent

        NavRail {
            id: rail
            height: parent.height
            currentTab: "library"
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
                title: libraryController.selectedChapter.length > 0 ? libraryController.selectedChapter : libraryController.selectedSubject
                profileText: appController.activeProfileName
                networkText: appController.networkLabel
                syncText: appController.syncLabel
                isOnline: appController.isOnline
                showBack: true
                onBackClicked: appController.navigate("chapters")
            }

            EmptyState {
                anchors.centerIn: parent
                visible: libraryController.packs.length === 0
                title: "No Practice Sets Found"
                description: "There are currently no practice packs for " + libraryController.selectedSubject + "."
                actionText: "Back to Topics"
                onActionClicked: appController.navigate("chapters")
            }

            ListView {
                width: parent.width
                height: parent.height - Metrics.headerHeight
                clip: true
                spacing: Spacing.sm
                topMargin: Spacing.xs
                bottomMargin: Spacing.md
                visible: libraryController.packs.length > 0
                model: libraryController.packs

                delegate: Item {
                    width: parent.width
                    height: 76

                    AppCard {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: parent.width - Spacing.xl
                        height: 70
                        interactive: true
                        onClicked: {
                            if (modelData.isInstalled) {
                                libraryController.selectPack(modelData.id, modelData.version);
                            } else {
                                libraryController.downloadPack(modelData.id, modelData.version);
                            }
                        }

                        Item {
                            anchors.fill: parent
                            anchors.leftMargin: Spacing.md
                            anchors.rightMargin: Spacing.md

                            Row {
                                anchors.left: parent.left
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: Spacing.md

                                // Subject Art Medallion
                                Image {
                                    width: 44
                                    height: 44
                                    anchors.verticalCenter: parent.verticalCenter
                                    source: Theme.subjectIcon(libraryController.selectedSubject)
                                    fillMode: Image.PreserveAspectFit
                                }

                                // Pack Title & Human-Friendly Info
                                Column {
                                    width: 420
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 3

                                    Text {
                                        text: modelData.title
                                        color: Theme.deepInk
                                        font.pixelSize: Typography.body
                                        font.bold: true
                                        font.family: Typography.fontFamily
                                        elide: Text.ElideRight
                                        width: parent.width
                                    }

                                    Text {
                                        text: modelData.questionCount + " questions • ~" + Math.max(5, Math.round(modelData.questionCount * 0.8)) + " mins • " + (modelData.isInstalled ? "Ready offline" : "Available to download")
                                        color: Theme.mutedInk
                                        font.pixelSize: Typography.caption
                                        font.family: Typography.fontFamily
                                    }
                                }
                            }

                            // Action Button: Start or Download
                            PrimaryButton {
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                preferredHeight: 46
                                text: modelData.isInstalled ? "Start →" : "Download"
                                buttonColor: modelData.isInstalled ? Theme.forest : Theme.surfaceActive
                                textColor: modelData.isInstalled ? Theme.textOnPrimary : Theme.deepInk
                                iconSource: modelData.isInstalled ? "" : Assets.download
                                onClicked: {
                                    if (modelData.isInstalled) {
                                        libraryController.selectPack(modelData.id, modelData.version);
                                    } else {
                                        libraryController.downloadPack(modelData.id, modelData.version);
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
