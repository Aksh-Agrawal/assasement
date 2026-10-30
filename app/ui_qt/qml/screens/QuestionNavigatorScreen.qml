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
        anchors.margins: 16

        Row {
            anchors.fill: parent
            spacing: 16

            // LEFT SUMMARY PANEL
            AppCard {
                width: 260
                height: parent.height

                Column {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 14

                    Text {
                        text: "Progress Summary"
                        color: Theme.textPrimary
                        font.pixelSize: Theme.fontSizeHeading
                        font.bold: true
                        font.family: Theme.fontFamily
                    }

                    Column {
                        width: parent.width
                        spacing: 10

                        // Answered
                        Row {
                            spacing: 10
                            Rectangle { width: 14; height: 14; radius: 7; color: Theme.success; anchors.verticalCenter: parent.verticalCenter }
                            Text { text: "✓ Answered:"; color: Theme.textSecondary; font.pixelSize: 15 }
                            Text { text: assessmentController.answeredCount + ""; font.bold: true; color: Theme.textPrimary; font.pixelSize: 15 }
                        }

                        // Unanswered
                        Row {
                            spacing: 10
                            Rectangle { width: 14; height: 14; radius: 7; color: Theme.border; anchors.verticalCenter: parent.verticalCenter }
                            Text { text: "○ Unanswered:"; color: Theme.textSecondary; font.pixelSize: 15 }
                            Text { text: assessmentController.unansweredCount + ""; font.bold: true; color: Theme.textPrimary; font.pixelSize: 15 }
                        }

                        // Flagged
                        Row {
                            spacing: 10
                            Rectangle { width: 14; height: 14; radius: 3; color: Theme.highlight; anchors.verticalCenter: parent.verticalCenter }
                            Text { text: "🚩 For Review:"; color: Theme.textSecondary; font.pixelSize: 15 }
                            Text { text: assessmentController.markedCount + ""; font.bold: true; color: Theme.textPrimary; font.pixelSize: 15 }
                        }
                    }

                    Item { Layout.fillHeight: true; height: 1 }

                    PrimaryButton {
                        width: parent.width
                        preferredHeight: Theme.touchNormal
                        text: "Submit Assessment"
                        onClicked: appController.navigate("submit_confirm")
                    }

                    SecondaryButton {
                        width: parent.width
                        preferredHeight: Theme.touchNormal
                        text: "Back to Question"
                        onClicked: appController.navigate("question")
                    }
                }
            }

            // RIGHT QUESTION GRID
            AppCard {
                width: parent.width - 260 - 16
                height: parent.height

                Column {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 14

                    Text {
                        text: "Tap any question to jump to it"
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontSizeCaption
                        font.bold: true
                        font.family: Theme.fontFamily
                    }

                    Grid {
                        width: parent.width
                        columns: 5
                        spacing: 12

                        Repeater {
                            model: assessmentController.navigatorList

                            delegate: Rectangle {
                                width: (parent.width - 48) / 5
                                height: 52
                                radius: 10

                                // Color & border based on status
                                color: {
                                    if (modelData.status === "flagged") return "#FFF3E0";
                                    if (modelData.status === "answered") return Theme.primaryLight;
                                    return Theme.surfaceActive;
                                }

                                border.color: {
                                    if (modelData.isCurrent) return Theme.primaryDark;
                                    if (modelData.status === "flagged") return Theme.highlight;
                                    if (modelData.status === "answered") return Theme.primary;
                                    return Theme.border;
                                }
                                border.width: modelData.isCurrent ? 3 : 1

                                Row {
                                    anchors.centerIn: parent
                                    spacing: 4

                                    Text {
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: modelData.index + ""
                                        font.pixelSize: Theme.fontSizeHeading
                                        font.bold: true
                                        color: modelData.status === "answered" ? Theme.primaryDark : Theme.textPrimary
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
