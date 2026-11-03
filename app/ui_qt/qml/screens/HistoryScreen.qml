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
            currentTab: "history"
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
                title: "Study Journal"
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

                EmptyState {
                    anchors.centerIn: parent
                    visible: assessmentController.historyList.length === 0
                    title: "No Completed Practice Yet"
                    description: "Your scores, answers, and study streaks will appear in this journal as you complete practice sets."
                    actionText: "Start a Practice Set"
                    onActionClicked: appController.navigate("subjects")
                }

                Column {
                    anchors.fill: parent
                    anchors.margins: Spacing.md
                    spacing: Spacing.sm
                    visible: assessmentController.historyList.length > 0

                    // Top Progress Journal Overview Card (Single, Tasteful)
                    AppCard {
                        width: parent.width - Spacing.md
                        height: 96
                        anchors.horizontalCenter: parent.horizontalCenter

                        Row {
                            anchors.fill: parent
                            anchors.margins: Spacing.md
                            spacing: Spacing.md

                            Column {
                                width: parent.width - 120
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 3

                                Text {
                                    text: "Your Learning Progress"
                                    color: Theme.deepInk
                                    font.pixelSize: Typography.sectionTitle
                                    font.bold: true
                                    font.family: Typography.familyEditorial
                                }

                                Text {
                                    text: assessmentController.historyList.length + " assessment(s) completed offline • High retention streak"
                                    color: Theme.mutedInk
                                    font.pixelSize: Typography.caption
                                    font.family: Typography.family
                                }

                                Row {
                                    spacing: Spacing.md
                                    Text {
                                        text: "Recent Mastery:"
                                        color: Theme.deepInk
                                        font.pixelSize: Typography.caption
                                        font.bold: true
                                    }
                                    Text {
                                        text: "79% average accuracy"
                                        color: Theme.forest
                                        font.pixelSize: Typography.caption
                                        font.bold: true
                                    }
                                }
                            }

                            Image {
                                width: 70
                                height: 70
                                anchors.verticalCenter: parent.verticalCenter
                                source: Assets.laurel_achievement
                                fillMode: Image.PreserveAspectFit
                            }
                        }
                    }

                    // Recent Completed Attempts Ledger
                    ListView {
                        width: parent.width
                        height: parent.height - 110
                        clip: true
                        spacing: Spacing.xs
                        topMargin: 2
                        bottomMargin: Spacing.md
                        model: assessmentController.historyList

                        delegate: Item {
                            width: parent.width
                            height: 60

                            AppCard {
                                anchors.horizontalCenter: parent.horizontalCenter
                                width: parent.width - Spacing.md
                                height: 56
                                interactive: true
                                onClicked: {
                                    appController.showNotification("Reviewing: " + modelData.title, "info");
                                }

                                Item {
                                    anchors.fill: parent
                                    anchors.leftMargin: Spacing.md
                                    anchors.rightMargin: Spacing.md

                                    Row {
                                        anchors.left: parent.left
                                        anchors.verticalCenter: parent.verticalCenter
                                        spacing: Spacing.md

                                        Image {
                                            width: 36
                                            height: 36
                                            anchors.verticalCenter: parent.verticalCenter
                                            source: Theme.subjectIcon(modelData.subject)
                                            fillMode: Image.PreserveAspectFit
                                        }

                                        Column {
                                            width: 440
                                            anchors.verticalCenter: parent.verticalCenter
                                            spacing: 2

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
                                                text: modelData.subject + " • " + modelData.completedAt + (modelData.synced ? " • Synced" : " • Stored locally")
                                                color: Theme.mutedInk
                                                font.pixelSize: Typography.caption
                                                font.family: Typography.fontFamily
                                            }
                                        }
                                    }

                                    // Score Pill
                                    Rectangle {
                                        anchors.right: parent.right
                                        anchors.verticalCenter: parent.verticalCenter
                                        width: 84
                                        height: 32
                                        radius: 16
                                        color: modelData.scorePercent >= 80 ? Theme.surfaceWarm : (modelData.scorePercent >= 60 ? "#FBF3DC" : "#FDF3EE")
                                        border.color: modelData.scorePercent >= 80 ? Theme.forest : (modelData.scorePercent >= 60 ? Theme.warmGold : Theme.terracotta)
                                        border.width: 1

                                        Text {
                                            anchors.centerIn: parent
                                            text: modelData.scorePercent + "%"
                                            color: modelData.scorePercent >= 80 ? Theme.forest : (modelData.scorePercent >= 60 ? Theme.deepInk : Theme.terracotta)
                                            font.pixelSize: Typography.caption
                                            font.bold: true
                                            font.family: Typography.fontFamily
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
}
