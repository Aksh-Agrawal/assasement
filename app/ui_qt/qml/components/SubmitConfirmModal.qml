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
    color: "#6623302D" // deep ink scrim

    // Dismiss on background click
    MouseArea {
        anchors.fill: parent
        onClicked: root.cancelClicked()
    }

    AppCard {
        anchors.centerIn: parent
        width: 520
        implicitHeight: modalCol.implicitHeight + Spacing.xl * 2

        // Prevent click-through
        MouseArea {
            anchors.fill: parent
        }

        Column {
            id: modalCol
            anchors.centerIn: parent
            width: parent.width - Spacing.xl * 2
            spacing: Spacing.md

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Submit Assessment?"
                color: Theme.textPrimary
                font.pixelSize: Typography.heroTitle
                font.family: Typography.fontSerif
                font.bold: true
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Review your completed responses before submitting."
                color: Theme.textSecondary
                font.pixelSize: Typography.body
                font.family: Typography.fontFamily
            }

            // Breakdown card
            Rectangle {
                width: parent.width
                height: 72
                radius: Metrics.radiusSm
                color: Theme.surfaceActive
                border.color: Theme.border
                border.width: 1

                Row {
                    anchors.centerIn: parent
                    spacing: Spacing.xl

                    // Answered
                    Column {
                        spacing: 2
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "✓ " + root.answeredCount
                            color: Theme.forest
                            font.pixelSize: Typography.pageTitle
                            font.family: Typography.fontSerif
                            font.bold: true
                        }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "Answered"
                            color: Theme.textSecondary
                            font.pixelSize: Typography.caption
                            font.family: Typography.fontFamily
                        }
                    }

                    Rectangle { width: 1; height: 36; color: Theme.divider; anchors.verticalCenter: parent.verticalCenter }

                    // Unanswered
                    Column {
                        spacing: 2
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "○ " + root.unansweredCount
                            color: root.unansweredCount > 0 ? Theme.terracotta : Theme.textSecondary
                            font.pixelSize: Typography.pageTitle
                            font.family: Typography.fontSerif
                            font.bold: true
                        }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "Unanswered"
                            color: Theme.textSecondary
                            font.pixelSize: Typography.caption
                            font.family: Typography.fontFamily
                        }
                    }

                    Rectangle { width: 1; height: 36; color: Theme.divider; anchors.verticalCenter: parent.verticalCenter }

                    // Marked for review
                    Column {
                        spacing: 2
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "🚩 " + root.markedCount
                            color: Theme.terracotta
                            font.pixelSize: Typography.pageTitle
                            font.family: Typography.fontSerif
                            font.bold: true
                        }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "For Review"
                            color: Theme.textSecondary
                            font.pixelSize: Typography.caption
                            font.family: Typography.fontFamily
                        }
                    }
                }
            }

            Item { width: 1; height: Spacing.xs }

            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: Spacing.md

                SecondaryButton {
                    text: "Review Answers"
                    preferredHeight: Metrics.touchNormal
                    onClicked: root.reviewClicked()
                }

                PrimaryButton {
                    text: "Submit Assessment"
                    preferredHeight: Metrics.touchNormal
                    onClicked: root.submitClicked()
                }
            }
        }
    }
}
