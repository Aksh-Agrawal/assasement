import QtQuick 2.15
import QtQuick.Controls 2.15 as Controls
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.canvas

    // -------------------------------------------------------------------------
    // Top Active Assessment Header (Compact 44px)
    // -------------------------------------------------------------------------
    Rectangle {
        id: questionHeader
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 44
        color: Theme.surface
        border.color: Theme.border
        border.width: 1

        Row {
            anchors.left: parent.left
            anchors.leftMargin: Spacing.md
            anchors.verticalCenter: parent.verticalCenter
            spacing: Spacing.md

            IconButton {
                buttonSize: 34
                iconSource: Assets.arrow_back
                onClicked: leaveModal.visible = true
            }

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: assessmentController.subject + (assessmentController.chapter.length > 0 ? " • " + assessmentController.chapter : "")
                color: Theme.deepInk
                font.pixelSize: Typography.sectionTitle
                font.bold: true
                font.family: Typography.family
                elide: Text.ElideRight
                width: 340
            }
        }

        Row {
            anchors.right: parent.right
            anchors.rightMargin: Spacing.md
            anchors.verticalCenter: parent.verticalCenter
            spacing: Spacing.md

            // Question counter (e.g. "4 / 10")
            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                height: 28
                width: counterText.implicitWidth + 18
                radius: 14
                color: Theme.surfaceActive
                border.color: Theme.border
                border.width: 1

                Text {
                    id: counterText
                    anchors.centerIn: parent
                    text: assessmentController.questionIndex + " / " + assessmentController.totalQuestions
                    color: Theme.deepInk
                    font.pixelSize: Typography.metadata
                    font.bold: true
                    font.family: Typography.family
                }
            }

            // Countdown timer (if enabled)
            Rectangle {
                visible: assessmentController.timerEnabled
                width: 78
                height: 28
                radius: 14
                color: assessmentController.remainingSeconds < 60 ? Theme.terracottaLight : Theme.surfaceActive
                border.color: assessmentController.remainingSeconds < 60 ? Theme.terracotta : Theme.border
                border.width: 1

                Row {
                    anchors.centerIn: parent
                    spacing: 4
                    Image {
                        anchors.verticalCenter: parent.verticalCenter
                        width: 13
                        height: 13
                        source: Assets.history
                        fillMode: Image.PreserveAspectFit
                    }
                    Text {
                        text: assessmentController.timerFormatted
                        font.pixelSize: 12
                        font.bold: true
                        color: assessmentController.remainingSeconds < 60 ? Theme.terracotta : Theme.deepInk
                    }
                }
            }

            // Flag / Mark for review button
            IconButton {
                buttonSize: 34
                iconSource: assessmentController.isMarkedForReview ? Assets.flag_filled : Assets.flag
                backgroundColor: assessmentController.isMarkedForReview ? Theme.goldLight : Theme.surface
                borderColor: assessmentController.isMarkedForReview ? Theme.gold : Theme.border
                onClicked: assessmentController.toggleMarkReview()
            }
        }

        // Thin progress indicator rail underneath header
        Rectangle {
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            height: 3
            color: Theme.borderLight

            Rectangle {
                height: parent.height
                width: parent.width * (assessmentController.totalQuestions > 0 ? (assessmentController.questionIndex / assessmentController.totalQuestions) : 0)
                color: Theme.forest
                Behavior on width {
                    NumberAnimation { duration: Theme.animDuration; easing.type: Easing.OutQuad }
                }
            }
        }
    }

    // -------------------------------------------------------------------------
    // Question Body & Options Area (Scrollable Flickable for long content)
    // -------------------------------------------------------------------------
    Flickable {
        id: scrollViewport
        anchors.top: questionHeader.bottom
        anchors.bottom: bottomActionBar.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: Spacing.md
        contentWidth: width
        contentHeight: questionColumn.implicitHeight + Spacing.sm
        clip: true

        EmptyState {
            anchors.centerIn: parent
            visible: !assessmentController.isActive || assessmentController.questionText.length === 0
            title: "No Question Available"
            description: "Please select an assessment pack from the library to begin practice."
            actionText: "Browse Library"
            onActionClicked: appController.navigate("subjects")
        }

        Column {
            id: questionColumn
            width: parent.width
            spacing: Spacing.md
            visible: assessmentController.isActive && assessmentController.questionText.length > 0

            // Academic Question Prompt Card
            Rectangle {
                width: parent.width
                implicitHeight: questionTextItem.implicitHeight + Spacing.lg
                radius: Metrics.radiusMedium
                color: Theme.surface
                border.color: Theme.border
                border.width: 1

                Item {
                    anchors.fill: parent
                    anchors.margins: Spacing.md

                    Text {
                        id: questionTextItem
                        anchors.fill: parent
                        text: assessmentController.questionText
                        color: Theme.deepInk
                        font.pixelSize: Typography.question
                        font.bold: true
                        font.family: Typography.family
                        wrapMode: Text.Wrap
                        lineHeight: 1.25
                    }
                }
            }

            Image {
                visible: source !== ""
                source: assessmentController.questionFigureSource
                width: parent.width
                height: visible ? 96 : 0
                fillMode: Image.PreserveAspectFit
                asynchronous: true
                cache: true
            }

            Column {
                width: parent.width
                spacing: Spacing.sm
                visible: assessmentController.numericalQuestion

                Controls.TextField {
                    id: numericalAnswer
                    width: parent.width
                    placeholderText: "Enter a number"
                    Accessible.name: "Numerical answer"
                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                    maximumLength: 64
                    onAccepted: if (submitNumber.enabled)
                        assessmentController.selectAnswer(text.trim())
                }

                Connections {
                    target: assessmentController
                    function onQuestionChanged() {
                        numericalAnswer.text = assessmentController.selectedKey
                    }
                }
                Connections {
                    target: appController
                    function onKeyboardSubmitted(text) {
                        if (appController.keyboardTarget === "numerical_answer")
                            numericalAnswer.text = text.trim()
                    }
                }
                Component.onCompleted: numericalAnswer.text = assessmentController.selectedKey

                Controls.Button {
                    text: "Open keyboard"
                    onClicked: appController.openKeyboard("numerical_answer",
                        numericalAnswer.text, false, "Enter numerical answer")
                }
                Controls.Button {
                    id: submitNumber
                    text: "Confirm answer"
                    enabled: assessmentController.numericalQuestion
                        && assessmentController.validNumericalAnswer(numericalAnswer.text)
                    onClicked: assessmentController.selectAnswer(numericalAnswer.text.trim())
                }
            }

            // 2-Column Responsive MCQ Option Cards Grid
            Grid {
                width: parent.width
                visible: !assessmentController.numericalQuestion
                columns: 2
                spacing: Spacing.md

                Repeater {
                    model: assessmentController.options

                    delegate: QuestionOption {
                        width: (parent.width - Spacing.md) / 2
                        optionKey: modelData.key
                        optionText: modelData.text
                        selected: modelData.selected
                        onClicked: {
                            assessmentController.selectAnswer(modelData.key);
                        }
                    }
                }
            }
        }
    }

    // -------------------------------------------------------------------------
    // Bottom Action Bar (Fixed 52px Touch Navigation)
    // -------------------------------------------------------------------------
    Rectangle {
        id: bottomActionBar
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 52
        color: Theme.surface
        border.color: Theme.border
        border.width: 1

        Row {
            anchors.left: parent.left
            anchors.leftMargin: Spacing.md
            anchors.verticalCenter: parent.verticalCenter
            spacing: Spacing.md

            SecondaryButton {
                preferredHeight: 42
                text: assessmentController.isMarkedForReview ? "Flagged" : "Mark for Review"
                borderColor: assessmentController.isMarkedForReview ? Theme.gold : Theme.border
                onClicked: assessmentController.toggleMarkReview()
            }

            SecondaryButton {
                preferredHeight: 42
                text: "Question Grid"
                iconSource: Assets.library
                onClicked: appController.navigate("question_nav")
            }
        }

        Row {
            anchors.right: parent.right
            anchors.rightMargin: Spacing.md
            anchors.verticalCenter: parent.verticalCenter
            spacing: Spacing.md

            SecondaryButton {
                preferredHeight: 42
                text: "← Previous"
                enabled: assessmentController.questionIndex > 1
                onClicked: assessmentController.previousQuestion()
            }

            PrimaryButton {
                preferredHeight: 42
                buttonColor: Theme.forest
                text: assessmentController.questionIndex === assessmentController.totalQuestions ? "Submit Test →" : "Next →"
                onClicked: {
                    if (assessmentController.questionIndex === assessmentController.totalQuestions) {
                        assessmentController.requestSubmit();
                    } else {
                        assessmentController.nextQuestion();
                    }
                }
            }
        }
    }

    // Modal: Pause & Leave Test Confirmation
    LeaveConfirmModal {
        id: leaveModal
        visible: false
        onPauseClicked: {
            leaveModal.visible = false;
            assessmentController.pauseAndExit();
        }
        onContinueClicked: {
            leaveModal.visible = false;
        }
    }
}
