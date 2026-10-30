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
                title: "Study History"
                profileText: appController.activeProfileName
                networkText: appController.networkLabel
                syncText: appController.syncLabel
                isOnline: appController.isOnline
                showBack: true
                onBackClicked: appController.navigate("home")
            }

            EmptyState {
                anchors.centerIn: parent
                visible: assessmentController.historyList.length === 0
                title: "No Completed Attempts Yet"
                description: "Assessments you complete will appear here with your scores."
                actionText: "Start a Practice Session"
                onActionClicked: appController.navigate("subjects")
            }

            ListView {
                width: parent.width
                height: parent.height - Theme.headerHeight
                clip: true
                spacing: 8
                topMargin: 8
                bottomMargin: 16
                visible: assessmentController.historyList.length > 0

                model: assessmentController.historyList

                delegate: Item {
                    width: parent.width
                    height: 64

                    AppCard {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: parent.width - 32
                        height: 60
                        interactive: true
                        onClicked: {
                            appController.showNotification("Reviewing: " + modelData.title, "info");
                        }

                        Row {
                            anchors.fill: parent
                            anchors.leftMargin: 16
                            anchors.rightMargin: 16
                            spacing: 14

                            Rectangle {
                                width: 40
                                height: 40
                                radius: 10
                                color: Theme.primaryLight
                                anchors.verticalCenter: parent.verticalCenter

                                Image {
                                    anchors.centerIn: parent
                                    width: 20
                                    height: 20
                                    source: Assets.history
                                    fillMode: Image.PreserveAspectFit
                                }
                            }

                            Column {
                                width: parent.width - 40 - 14 - 120
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 2

                                Text {
                                    text: modelData.title
                                    color: Theme.textPrimary
                                    font.pixelSize: Theme.fontSizeBody
                                    font.bold: true
                                    font.family: Theme.fontFamily
                                    elide: Text.ElideRight
                                }

                                Text {
                                    text: modelData.subject + " • " + modelData.completedAt + (modelData.synced ? " • Synced ✓" : " • Local")
                                    color: Theme.textSecondary
                                    font.pixelSize: Theme.fontSizeCaption
                                    font.family: Theme.fontFamily
                                }
                            }

                            // Score pill
                            Rectangle {
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                width: 72
                                height: 36
                                radius: 18
                                color: modelData.scorePercent >= 80 ? "#E8F5E9" : (modelData.scorePercent >= 60 ? "#FFF3E0" : "#FFEBEE")
                                border.color: modelData.scorePercent >= 80 ? Theme.success : (modelData.scorePercent >= 60 ? Theme.highlight : Theme.warning)

                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.scorePercent + "%"
                                    color: modelData.scorePercent >= 80 ? Theme.success : (modelData.scorePercent >= 60 ? "#C86400" : Theme.warning)
                                    font.pixelSize: 15
                                    font.bold: true
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
