import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.canvas
    property var progress: assessmentController.historyAnalytics

    function displayDuration(milliseconds) {
        var totalMinutes = Math.floor(milliseconds / 60000)
        var hours = Math.floor(totalMinutes / 60)
        var minutes = totalMinutes % 60
        if (hours > 0) return hours + "h " + minutes + "m"
        return minutes + "m"
    }

    function displayAnswerTime(milliseconds) {
        if (milliseconds < 0) return "—"
        if (milliseconds < 60000) return Math.round(milliseconds / 1000) + " sec"
        return Math.floor(milliseconds / 60000) + "m " + Math.round(milliseconds % 60000 / 1000) + "s"
    }

    function syncStatusLabel(status) {
        if (status === "synced") return "Synced"
        if (status === "failed") return "Sync failed — will retry"
        if (status === "pending") return "Waiting to sync"
        return "Stored on this device"
    }

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
                else if (tab === "progress") appController.navigate("progress");
                else if (tab === "history") appController.navigate("history");
                else if (tab === "settings") appController.navigate("settings");
            }
        }

        Column {
            width: parent.width - rail.width
            height: parent.height

            AppHeader {
                width: parent.width
                title: "Assessment History"
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

                    // Local and profile-authorized cloud attempts.
                    ListView {
                        width: parent.width
                        height: parent.height
                        clip: true
                        spacing: Spacing.xs
                        topMargin: 2
                        bottomMargin: Spacing.md
                        model: assessmentController.historyList

                        delegate: Item {
                            width: parent.width
                            height: 60

                            AppCard {
                                objectName: "history-row-" + modelData.attemptId
                                anchors.horizontalCenter: parent.horizontalCenter
                                width: parent.width - Spacing.md
                                height: 56
                                interactive: true
                                onClicked: {
                                    assessmentController.openHistoryReview(modelData.attemptId);
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
                                                text: modelData.subject + " · " + (modelData.source === "web" ? "Web" : (modelData.source === "device" ? "Raspberry Pi" : "Source unknown")) + " · " + modelData.completedAt + " · " + root.syncStatusLabel(modelData.syncStatus)
                                                color: Theme.mutedInk
                                                font.pixelSize: Typography.caption
                                                font.family: Typography.fontFamily
                                                width: parent.width - 110
                                                elide: Text.ElideRight
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
                                        color: modelData.scorePercent < 0 ? Theme.surfaceSelected : (modelData.scorePercent >= 80 ? Theme.primaryLight : (modelData.scorePercent >= 60 ? "#FBF3DC" : "#FDF3EE"))
                                        border.color: modelData.scorePercent < 0 ? Theme.border : (modelData.scorePercent >= 80 ? Theme.forest : (modelData.scorePercent >= 60 ? Theme.gold : Theme.terracotta))
                                        border.width: 1

                                        Text {
                                            anchors.centerIn: parent
                                            text: modelData.scorePercent < 0 ? "Saved" : modelData.scorePercent + "%"
                                            color: modelData.scorePercent < 0 ? Theme.mutedInk : (modelData.scorePercent >= 80 ? Theme.forest : (modelData.scorePercent >= 60 ? Theme.deepInk : Theme.terracotta))
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
