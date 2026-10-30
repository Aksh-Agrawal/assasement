import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.background

    // Active Assessment Header (Full 800px width)
    Rectangle {
        id: questionHeader
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 52
        color: Theme.surface
        border.color: Theme.divider
        border.width: 1

        Row {
            anchors.left: parent.left
            anchors.leftMargin: 16
            anchors.verticalCenter: parent.verticalCenter
            spacing: 12

            IconButton {
                buttonSize: 38
                iconSource: "../icons/arrow_back.svg"
                onClicked: leaveModal.visible = true
            }

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: assessmentController.subject + (assessmentController.chapter.length > 0 ? " • " + assessmentController.chapter : "")
                color: Theme.textPrimary
                font.pixelSize: Theme.fontSizeHeading
                font.bold: true
                font.family: Theme.fontFamily
            }
        }

        Row {
            anchors.right: parent.right
            anchors.rightMargin: 16
            anchors.verticalCenter: parent.verticalCenter
            spacing: 14

            // Question counter
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: "Question " + assessmentController.questionIndex + " of " + assessmentController.totalQuestions
                color: Theme.textSecondary
                font.pixelSize: Theme.fontSizeBody
                font.bold: true
                font.family: Theme.fontFamily
            }

            // Countdown timer (if enabled)
            Rectangle {
                visible: assessmentController.timerEnabled
                width: 82
                height: 32
                radius: 16
                color: assessmentController.remainingSeconds < 60 ? "#FFEBEE" : Theme.surfaceActive
                border.color: assessmentController.remainingSeconds < 60 ? Theme.warning : Theme.border

                Row {
                    anchors.centerIn: parent
                    spacing: 4
                    Text { text: "⏱"; font.pixelSize: 12 }
                    Text {
                        text: assessmentController.timerFormatted
                        font.pixelSize: 13
                        font.bold: true
                        color: assessmentController.remainingSeconds < 60 ? Theme.warning : Theme.textPrimary
                    }
                }
            }

            // Flag / Mark for review button
            IconButton {
                buttonSize: 38
                iconSource: assessmentController.isMarkedForReview ? "../icons/flag_filled.svg" : "../icons/flag.svg"
                backgroundColor: assessmentController.isMarkedForReview ? "#FFF3E0" : Theme.surface
                onClicked: assessmentController.toggleMarkReview()
            }
        }
    }

    // Question Body & Options Area
    Item {
        anchors.top: questionHeader.bottom
        anchors.bottom: bottomActionBar.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 14

        Column {
            anchors.fill: parent
            spacing: 12

            // Question Text (Flickable for long text)
            Flickable {
                width: parent.width
                height: Math.min(100, questionContentText.implicitHeight + 10)
                contentWidth: width
                contentHeight: questionContentText.implicitHeight
                clip: true

                Text {
                    id: questionContentText
                    width: parent.width
                    text: assessmentController.questionText
                    color: Theme.textPrimary
                    font.pixelSize: Theme.fontSizeHeading
                    font.bold: true
                    font.family: Theme.fontFamily
                    wrapMode: Text.Wrap
                }
            }

            // 2x2 MCQ Option Cards Grid (Takes the remaining vertical space comfortably)
            Grid {
                width: parent.width
                columns: 2
                spacing: 12

                Repeater {
                    model: assessmentController.options

                    delegate: QuestionOption {
                        width: (parent.width - 12) / 2
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

    // Bottom Action Bar
    Rectangle {
        id: bottomActionBar
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 64
        color: Theme.surface
        border.color: Theme.divider
        border.width: 1

        Row {
            anchors.left: parent.left
            anchors.leftMargin: 16
            anchors.verticalCenter: parent.verticalCenter
            spacing: 12

            SecondaryButton {
                preferredHeight: 48
                text: assessmentController.isMarkedForReview ? "Flagged for Review 🚩" : "Mark for Review"
                borderColor: assessmentController.isMarkedForReview ? Theme.highlight : Theme.border
                onClicked: assessmentController.toggleMarkReview()
            }

            SecondaryButton {
                preferredHeight: 48
                text: "Question Grid"
                iconSource: "../icons/library.svg"
                onClicked: appController.navigate("question_nav")
            }
        }

        Row {
            anchors.right: parent.right
            anchors.rightMargin: 16
            anchors.verticalCenter: parent.verticalCenter
            spacing: 12

            SecondaryButton {
                preferredHeight: 48
                text: "← Previous"
                enabled: assessmentController.questionIndex > 1
                onClicked: assessmentController.previousQuestion()
            }

            PrimaryButton {
                preferredHeight: 48
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
