import QtQuick 2.15
import ".." 1.0

Rectangle {
    id: root

    property int answeredCount: 0
    property int unansweredCount: 0
    property int markedCount: 0

    signal reviewClicked()
    signal submitClicked()
    signal cancelClicked()

    anchors.fill: parent
    color: "#802E2E2E" // semi-transparent backdrop

    // Dismiss on background click
    MouseArea {
        anchors.fill: parent
        onClicked: root.cancelClicked()
    }

    AppCard {
        anchors.centerIn: parent
        width: 520
        implicitHeight: modalCol.implicitHeight + 48

        // Prevent click-through
        MouseArea {
            anchors.fill: parent
        }

        Column {
            id: modalCol
            anchors.centerIn: parent
            width: parent.width - 48
            spacing: 16

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Ready to submit?"
                color: Theme.textPrimary
                font.pixelSize: Theme.fontSizeTitle
                font.bold: true
                font.family: Theme.fontFamily
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Great job completing your practice!"
                color: Theme.textSecondary
                font.pixelSize: Theme.fontSizeSecondary
                font.family: Theme.fontFamily
            }

            // Breakdown card
            Rectangle {
                width: parent.width
                height: 72
                radius: 12
                color: Theme.surfaceActive
                border.color: Theme.border
                border.width: 1

                Row {
                    anchors.centerIn: parent
                    spacing: 24

                    // Answered
                    Column {
                        spacing: 2
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "✓ " + root.answeredCount
                            color: Theme.success
                            font.pixelSize: Theme.fontSizeHeading
                            font.bold: true
                        }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "Answered"
                            color: Theme.textSecondary
                            font.pixelSize: Theme.fontSizeCaption
                        }
                    }

                    Rectangle { width: 1; height: 36; color: Theme.divider; anchors.verticalCenter: parent.verticalCenter }

                    // Unanswered
                    Column {
                        spacing: 2
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "○ " + root.unansweredCount
                            color: root.unansweredCount > 0 ? Theme.warning : Theme.textSecondary
                            font.pixelSize: Theme.fontSizeHeading
                            font.bold: true
                        }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "Unanswered"
                            color: Theme.textSecondary
                            font.pixelSize: Theme.fontSizeCaption
                        }
                    }

                    Rectangle { width: 1; height: 36; color: Theme.divider; anchors.verticalCenter: parent.verticalCenter }

                    // Marked for review
                    Column {
                        spacing: 2
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "🚩 " + root.markedCount
                            color: Theme.highlight
                            font.pixelSize: Theme.fontSizeHeading
                            font.bold: true
                        }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "For Review"
                            color: Theme.textSecondary
                            font.pixelSize: Theme.fontSizeCaption
                        }
                    }
                }
            }

            Item { width: 1; height: 4 }

            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 16

                SecondaryButton {
                    text: "Review Answers"
                    preferredHeight: Theme.touchNormal
                    onClicked: root.reviewClicked()
                }

                PrimaryButton {
                    text: "Submit Assessment"
                    preferredHeight: Theme.touchNormal
                    onClicked: root.submitClicked()
                }
            }
        }
    }
}
