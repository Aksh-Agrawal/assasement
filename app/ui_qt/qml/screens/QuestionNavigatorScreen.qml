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
        title: "Question Navigator"
        showBack: true
        onBackClicked: appController.navigate("question")
    }

    Item {
        anchors.top: header.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: Spacing.md

        Row {
            anchors.fill: parent
            spacing: Spacing.md

            // LEFT SUMMARY PANEL
            AppCard {
                width: 250
                height: parent.height

                Column {
                    anchors.fill: parent
                    anchors.margins: Spacing.lg
                    spacing: Spacing.sm

                    Text {
                        text: "Progress Ledger"
                        color: Theme.textPrimary
                        font.pixelSize: Typography.sectionTitle
                        font.family: Typography.fontSerif
                        font.bold: true
                    }

                    Column {
                        width: parent.width
                        spacing: Spacing.sm

                        // Answered
                        Row {
                            spacing: Spacing.sm
                            Rectangle { width: 12; height: 12; radius: 6; color: Theme.forest; anchors.verticalCenter: parent.verticalCenter }
                            Text { text: "Completed:"; color: Theme.textSecondary; font.pixelSize: Typography.metadata; font.family: Typography.fontFamily }
                            Text { text: assessmentController.answeredCount + ""; font.bold: true; color: Theme.forest; font.pixelSize: Typography.metadata }
                        }

                        // Unanswered
                        Row {
                            spacing: Spacing.sm
                            Rectangle { width: 12; height: 12; radius: 6; color: Theme.border; anchors.verticalCenter: parent.verticalCenter }
                            Text { text: "Unanswered:"; color: Theme.textSecondary; font.pixelSize: Typography.metadata; font.family: Typography.fontFamily }
                            Text { text: assessmentController.unansweredCount + ""; font.bold: true; color: Theme.textPrimary; font.pixelSize: Typography.metadata }
                        }

                        // Flagged
                        Row {
                            spacing: Spacing.sm
                            Rectangle { width: 12; height: 12; radius: 3; color: Theme.terracotta; anchors.verticalCenter: parent.verticalCenter }
                            Text { text: "Flagged:"; color: Theme.textSecondary; font.pixelSize: Typography.metadata; font.family: Typography.fontFamily }
                            Text { text: assessmentController.markedCount + ""; font.bold: true; color: Theme.terracotta; font.pixelSize: Typography.metadata }
                        }
                    }

                    Item { width: 1; height: Spacing.xs }

                    PrimaryButton {
                        width: parent.width
                        preferredHeight: Metrics.touchNormal
                        text: "Submit Assessment"
                        onClicked: appController.navigate("submit_confirm")
                    }

                    SecondaryButton {
                        width: parent.width
                        preferredHeight: Metrics.touchNormal
                        text: "Back to Question"
                        onClicked: appController.navigate("question")
                    }
                }
            }

            // RIGHT QUESTION GRID
            AppCard {
                width: parent.width - 250 - Spacing.md
                height: parent.height

                Column {
                    anchors.fill: parent
                    anchors.margins: Spacing.lg
                    spacing: Spacing.sm

                    Text {
                        text: "Select a question to jump to it"
                        color: Theme.textSecondary
                        font.pixelSize: Typography.caption
                        font.family: Typography.fontFamily
                    }

                    Grid {
                        width: parent.width
                        columns: 5
                        spacing: Spacing.sm

                        Repeater {
                            model: assessmentController.navigatorList

                            delegate: Rectangle {
                                width: (parent.width - Spacing.sm * 4) / 5
                                height: 50
                                radius: Metrics.radiusSm

                                // Color & border based on status
                                color: {
                                    if (modelData.status === "flagged") return "#FDF3EE"; // subtle warm terracotta wash
                                    if (modelData.status === "answered") return Theme.surfaceWarm;
                                    return Theme.surface;
                                }

                                border.color: {
                                    if (modelData.isCurrent) return Theme.forest;
                                    if (modelData.status === "flagged") return Theme.terracotta;
                                    if (modelData.status === "answered") return Theme.softSage;
                                    return Theme.border;
                                }
                                border.width: modelData.isCurrent ? 2 : 1

                                Row {
                                    anchors.centerIn: parent
                                    spacing: 4

                                    Text {
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: modelData.index + ""
                                        font.pixelSize: Typography.sectionTitle
                                        font.family: Typography.fontSerif
                                        font.bold: true
                                        color: modelData.isCurrent ? Theme.forest : (modelData.status === "answered" ? Theme.forest : Theme.textPrimary)
                                    }

                                    Text {
                                        anchors.verticalCenter: parent.verticalCenter
                                        font.pixelSize: 12
                                        text: {
                                            if (modelData.status === "flagged") return "🚩";
                                            if (modelData.status === "answered") return "✓";
                                            return "";
                                        }
                                    }
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        assessmentController.goToQuestion(modelData.index);
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
