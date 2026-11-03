import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.canvas

    property int timerMinutes: 0
    property string selectedMode: "practice" // "practice", "test", "challenge"

    AppHeader {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        title: "Test Setup"
        networkText: appController.networkLabel
        syncText: appController.syncLabel
        isOnline: appController.isOnline
        showBack: true
        onBackClicked: appController.navigate("packs")
    }

    Item {
        anchors.top: header.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: Spacing.lg

        Row {
            anchors.fill: parent
            spacing: Spacing.lg

            // LEFT PANEL: Pack Overview
            AppCard {
                width: 290
                height: parent.height

                Column {
                    anchors.fill: parent
                    anchors.margins: Spacing.lg
                    spacing: Spacing.md

                    // Subject Art Medallion
                    Image {
                        width: 56
                        height: 56
                        source: Theme.subjectIcon(libraryController.selectedPack.subject)
                        fillMode: Image.PreserveAspectFit
                    }

                    Text {
                        text: libraryController.selectedPack.title || "Assessment"
                        color: Theme.deepInk
                        font.pixelSize: Typography.sectionTitle
                        font.bold: true
                        font.family: Typography.family
                        wrapMode: Text.Wrap
                        width: parent.width
                    }

                    Text {
                        text: (libraryController.selectedPack.subject || "") + (libraryController.selectedPack.chapter ? " • " + libraryController.selectedPack.chapter : "")
                        color: Theme.mutedInk
                        font.pixelSize: Typography.body
                        font.family: Typography.family
                    }

                    Rectangle {
                        width: parent.width
                        height: 1
                        color: Theme.borderLight
                    }

                    Row {
                        spacing: Spacing.sm
                        Text { text: "Questions:"; color: Theme.mutedInk; font.pixelSize: Typography.body }
                        Text { text: (libraryController.selectedPack.questionCount || 10) + " items"; font.bold: true; color: Theme.deepInk; font.pixelSize: Typography.body }
                    }

                    Row {
                        spacing: Spacing.sm
                        Text { text: "Device status:"; color: Theme.mutedInk; font.pixelSize: Typography.body }
                        Text { text: "Ready offline ✓"; font.bold: true; color: Theme.forest; font.pixelSize: Typography.body }
                    }
                }
            }

            // RIGHT PANEL: Configuration & Start
            AppCard {
                width: parent.width - 290 - Spacing.lg
                height: parent.height

                Column {
                    anchors.fill: parent
                    anchors.margins: Spacing.lg
                    spacing: Spacing.md

                    // Timer setting
                    Column {
                        spacing: Spacing.xs
                        width: parent.width

                        Text {
                            text: "Timer Options"
                            color: Theme.deepInk
                            font.pixelSize: Typography.body
                            font.bold: true
                            font.family: Typography.family
                        }

                        Row {
                            spacing: Spacing.sm
                            Repeater {
                                model: [
                                    { label: "No timer", mins: 0 },
                                    { label: "10 min", mins: 10 },
                                    { label: "20 min", mins: 20 }
                                ]
                                delegate: Rectangle {
                                    width: 124
                                    height: 46
                                    radius: Metrics.radiusMedium
                                    color: root.timerMinutes === modelData.mins ? Theme.primaryLight : Theme.surfaceActive
                                    border.color: root.timerMinutes === modelData.mins ? Theme.forest : Theme.border
                                    border.width: root.timerMinutes === modelData.mins ? 2 : 1

                                    Text {
                                        anchors.centerIn: parent
                                        text: modelData.label
                                        font.pixelSize: Typography.body
                                        font.bold: root.timerMinutes === modelData.mins
                                        color: root.timerMinutes === modelData.mins ? Theme.forest : Theme.deepInk
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: root.timerMinutes = modelData.mins
                                    }
                                }
                            }
                        }
                    }

                    // Mode setting
                    Column {
                        spacing: Spacing.xs
                        width: parent.width

                        Text {
                            text: "Practice Mode"
                            color: Theme.deepInk
                            font.pixelSize: Typography.body
                            font.bold: true
                            font.family: Typography.family
                        }

                        Row {
                            spacing: Spacing.sm
                            Repeater {
                                model: [
                                    { id: "practice", label: "Practice", desc: "Hints & feedback" },
                                    { id: "test", label: "Timed Test", desc: "Results at end" },
                                    { id: "challenge", label: "Challenge", desc: "No second chances" }
                                ]
                                delegate: Rectangle {
                                    width: 124
                                    height: 58
                                    radius: Metrics.radiusMedium
                                    color: root.selectedMode === modelData.id ? Theme.primaryLight : Theme.surfaceActive
                                    border.color: root.selectedMode === modelData.id ? Theme.forest : Theme.border
                                    border.width: root.selectedMode === modelData.id ? 2 : 1

                                    Column {
                                        anchors.centerIn: parent
                                        spacing: 2
                                        Text {
                                            anchors.horizontalCenter: parent.horizontalCenter
                                            text: modelData.label
                                            font.pixelSize: Typography.body
                                            font.bold: true
                                            color: root.selectedMode === modelData.id ? Theme.forest : Theme.deepInk
                                        }
                                        Text {
                                            anchors.horizontalCenter: parent.horizontalCenter
                                            text: modelData.desc
                                            font.pixelSize: 11
                                            color: Theme.mutedInk
                                        }
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: root.selectedMode = modelData.id
                                    }
                                }
                            }
                        }
                    }

                    Item { width: 1; height: Spacing.xs }

                    // Bottom action buttons
                    Row {
                        anchors.right: parent.right
                        spacing: Spacing.md

                        SecondaryButton {
                            text: "Back"
                            preferredHeight: Metrics.touchNormal
                            onClicked: appController.navigate("packs")
                        }

                        PrimaryButton {
                            text: "Begin Assessment →"
                            preferredHeight: Metrics.touchNormal
                            buttonColor: Theme.forest
                            onClicked: {
                                assessmentController.startTest(root.selectedMode, root.timerMinutes);
                            }
                        }
                    }
                }
            }
        }
    }
}
