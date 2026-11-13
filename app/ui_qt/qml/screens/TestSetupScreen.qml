import QtQuick 2.15
import QtQuick.Controls 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.canvas

    property int timerMinutes: 0
    property string selectedMode: "practice" // "practice", "test", "challenge"
    function difficultyValue(label) { return label === "Any difficulty" ? "" : label.toLowerCase(); }
    function topicValue() { return topicPicker.currentIndex === 0 ? "" : topicPicker.currentText; }

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
                        Text { text: "Ready offline"; font.bold: true; color: Theme.forest; font.pixelSize: Typography.body }
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

                    // Pack-backed practice filters. The selected order is saved with the attempt.
                    Column {
                        width: parent.width
                        spacing: Spacing.xs
                        Text { text: "Practice Questions"; color: Theme.deepInk; font.pixelSize: Typography.body; font.bold: true }
                        Row {
                            width: parent.width
                            spacing: 8
                            Column {
                                width: (parent.width - 16) / 3
                                spacing: 3
                                Text { text: "Topic"; color: Theme.mutedInk; font.pixelSize: 11 }
                                ComboBox {
                                    id: topicPicker
                                    width: parent.width
                                    height: 40
                                    model: libraryController.practiceTopics
                                    onActivated: {
                                        countPresetPicker.currentIndex = 0
                                        customCountLabel.visible = false
                                        countPicker.value = countPicker.to
                                    }
                                    contentItem: Text {
                                        text: topicPicker.displayText
                                        leftPadding: 10
                                        rightPadding: 22
                                        verticalAlignment: Text.AlignVCenter
                                        elide: Text.ElideRight
                                        color: Theme.deepInk
                                        font.pixelSize: Typography.caption
                                        font.family: Typography.family
                                    }
                                    background: Rectangle {
                                        radius: 7
                                        color: Theme.surfaceActive
                                        border.color: topicPicker.activeFocus ? Theme.forest : Theme.border
                                    }
                                    indicator: Text {
                                        text: "▼"
                                        anchors.right: parent.right
                                        anchors.rightMargin: 9
                                        anchors.verticalCenter: parent.verticalCenter
                                        color: Theme.mutedInk
                                        font.pixelSize: 14
                                    }
                                }
                            }
                            Column {
                                width: (parent.width - 16) / 3
                                spacing: 3
                                Text { text: "Difficulty"; color: Theme.mutedInk; font.pixelSize: 11 }
                                ComboBox {
                                    id: difficultyPicker; width: parent.width; height: 40
                                    model: ["Any difficulty", "Foundation", "Standard", "Challenge"]
                                    contentItem: Text { text: difficultyPicker.displayText; leftPadding: 10; rightPadding: 22; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight; color: Theme.deepInk; font.pixelSize: Typography.caption; font.family: Typography.family }
                                    background: Rectangle { radius: 7; color: Theme.surfaceActive; border.color: difficultyPicker.activeFocus ? Theme.forest : Theme.border }
                                    indicator: Text { text: "▼"; anchors.right: parent.right; anchors.rightMargin: 9; anchors.verticalCenter: parent.verticalCenter; color: Theme.mutedInk; font.pixelSize: 14 }
                                    onActivated: {
                                        countPicker.value = Math.min(countPicker.value, countPicker.to)
                                        countPresetPicker.currentIndex = 0
                                        customCountLabel.visible = false
                                    }
                                }
                            }
                            Column {
                                width: (parent.width - 16) / 3
                                spacing: 3
                                Text { text: "Question count"; color: Theme.mutedInk; font.pixelSize: 11 }
                                ComboBox {
                                    id: countPresetPicker; width: parent.width; height: 40
                                    model: libraryController.practiceCountPresets(topicPicker.currentText, difficultyPicker.currentText)
                                    contentItem: Text { text: countPresetPicker.displayText; leftPadding: 8; rightPadding: 21; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight; color: Theme.deepInk; font.pixelSize: 11; font.family: Typography.family }
                                    background: Rectangle { radius: 7; color: Theme.surfaceActive; border.color: countPresetPicker.activeFocus ? Theme.forest : Theme.border }
                                    indicator: Text { text: "▼"; anchors.right: parent.right; anchors.rightMargin: 8; anchors.verticalCenter: parent.verticalCenter; color: Theme.mutedInk; font.pixelSize: 14 }
                                    onActivated: {
                                        customCountLabel.visible = currentText === "Custom"
                                        if (currentText === "All questions")
                                            countPicker.value = countPicker.to
                                        else if (currentText !== "Custom")
                                            countPicker.value = parseInt(currentText, 10)
                                    }
                                }
                                SpinBox {
                                    id: countPicker; width: parent.width; height: 40
                                    visible: customCountLabel.visible
                                    from: 1
                                    to: Math.max(1, libraryController.practiceQuestionCount(topicPicker.currentText, difficultyPicker.currentText))
                                    value: to
                                    editable: true
                                    onToChanged: value = Math.min(value, to)
                                    onValueModified: countPresetPicker.currentIndex = countPresetPicker.count - 1
                                }
                                Text {
                                    id: customCountLabel
                                    visible: false
                                    text: "Custom question count"
                                    color: Theme.mutedInk
                                    font.pixelSize: 10
                                }
                            }
                        }
                        Text {
                            visible: libraryController.practiceQuestionCount(topicPicker.currentText, difficultyPicker.currentText) === 0
                            text: "No questions match these filters. Choose another topic or difficulty."
                            color: Theme.terracotta
                            font.pixelSize: Typography.caption
                            wrapMode: Text.Wrap
                            width: parent.width
                        }
                        CheckBox { id: shufflePicker; text: "Shuffle questions"; checked: false; implicitHeight: 36 }
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
                            enabled: libraryController.practiceQuestionCount(topicPicker.currentText, difficultyPicker.currentText) > 0
                            onClicked: {
                                assessmentController.startTest(root.selectedMode, root.timerMinutes, countPicker.value, root.difficultyValue(difficultyPicker.currentText), root.topicValue(), shufflePicker.checked);
                            }
                        }
                    }
                }
            }
        }
    }
}
