import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.background

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
        anchors.margins: 16

        Row {
            anchors.fill: parent
            spacing: 16

            // LEFT PANEL: Pack Overview
            AppCard {
                width: 300
                height: parent.height

                Column {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 12

                    Rectangle {
                        width: 52
                        height: 52
                        radius: 14
                        color: Theme.primaryLight

                        Image {
                            anchors.centerIn: parent
                            width: 28
                            height: 28
                            source: "../icons/practice.svg"
                            fillMode: Image.PreserveAspectFit
                        }
                    }

                    Text {
                        text: libraryController.selectedPack.title || "Assessment"
                        color: Theme.textPrimary
                        font.pixelSize: Theme.fontSizeHeading
                        font.bold: true
                        font.family: Theme.fontFamily
                        wrapMode: Text.Wrap
                        width: parent.width
                    }

                    Text {
                        text: (libraryController.selectedPack.subject || "") + " • " + (libraryController.selectedPack.chapter || "")
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontSizeSecondary
                        font.family: Theme.fontFamily
                    }

                    Rectangle {
                        width: parent.width
                        height: 1
                        color: Theme.divider
                    }

                    Row {
                        spacing: 8
                        Text { text: "Questions:"; color: Theme.textSecondary; font.pixelSize: 14 }
                        Text { text: (libraryController.selectedPack.questionCount || 10) + " items"; font.bold: true; color: Theme.textPrimary; font.pixelSize: 14 }
                    }

                    Row {
                        spacing: 8
                        Text { text: "Device state:"; color: Theme.textSecondary; font.pixelSize: 14 }
                        Text { text: "Ready offline ✓"; font.bold: true; color: Theme.success; font.pixelSize: 14 }
                    }
                }
            }

            // RIGHT PANEL: Settings & Start Action
            AppCard {
                width: parent.width - 300 - 16
                height: parent.height

                Column {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 14

                    // Timer setting
                    Column {
                        spacing: 6
                        width: parent.width

                        Text {
                            text: "Timer Options"
                            color: Theme.textSecondary
                            font.pixelSize: Theme.fontSizeCaption
                            font.bold: true
                        }

                        Row {
                            spacing: 10
                            Repeater {
                                model: [
                                    { label: "No timer", mins: 0 },
                                    { label: "10 min", mins: 10 },
                                    { label: "20 min", mins: 20 }
                                ]
                                delegate: Rectangle {
                                    width: 130
                                    height: 48
                                    radius: 10
                                    color: root.timerMinutes === modelData.mins ? Theme.primaryLight : Theme.surfaceActive
                                    border.color: root.timerMinutes === modelData.mins ? Theme.primary : Theme.border
                                    border.width: root.timerMinutes === modelData.mins ? 2 : 1

                                    Text {
                                        anchors.centerIn: parent
                                        text: modelData.label
                                        font.pixelSize: 14
                                        font.bold: root.timerMinutes === modelData.mins
                                        color: root.timerMinutes === modelData.mins ? Theme.primaryDark : Theme.textPrimary
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: root.timerMinutes = modelData.mins
                                    }
                                }
                            }
                        }
                    }

                    // Mode setting
                    Column {
                        spacing: 6
                        width: parent.width

                        Text {
                            text: "Practice Mode"
                            color: Theme.textSecondary
                            font.pixelSize: Theme.fontSizeCaption
                            font.bold: true
                        }

                        Row {
                            spacing: 10
                            Repeater {
                                model: [
                                    { id: "practice", label: "Practice", desc: "Hints & feedback" },
                                    { id: "test", label: "Test", desc: "Results at end" },
                                    { id: "challenge", label: "Challenge", desc: "No second chances" }
                                ]
                                delegate: Rectangle {
                                    width: 130
                                    height: 60
                                    radius: 10
                                    color: root.selectedMode === modelData.id ? Theme.primaryLight : Theme.surfaceActive
                                    border.color: root.selectedMode === modelData.id ? Theme.primary : Theme.border
                                    border.width: root.selectedMode === modelData.id ? 2 : 1

                                    Column {
                                        anchors.centerIn: parent
                                        spacing: 2
                                        Text {
                                            anchors.horizontalCenter: parent.horizontalCenter
                                            text: modelData.label
                                            font.pixelSize: 14
                                            font.bold: true
                                            color: root.selectedMode === modelData.id ? Theme.primaryDark : Theme.textPrimary
                                        }
                                        Text {
                                            anchors.horizontalCenter: parent.horizontalCenter
                                            text: modelData.desc
                                            font.pixelSize: 11
                                            color: Theme.textSecondary
                                        }
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: root.selectedMode = modelData.id
                                    }
                                }
                            }
                        }
                    }

                    Item { Layout.fillHeight: true; height: 1 }

                    // Bottom start button
                    Row {
                        anchors.right: parent.right
                        spacing: 12

                        SecondaryButton {
                            text: "Back"
                            preferredHeight: Theme.touchLarge
                            onClicked: appController.navigate("packs")
                        }

                        PrimaryButton {
                            text: "Start Assessment →"
                            preferredHeight: Theme.touchLarge
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
