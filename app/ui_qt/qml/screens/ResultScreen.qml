import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.canvas

    Column {
        anchors.centerIn: parent
        spacing: Spacing.md
        width: 620

        AppCard {
            width: parent.width
            implicitHeight: contentCol.implicitHeight + Spacing.xl * 2

            Column {
                id: contentCol
                anchors.centerIn: parent
                width: parent.width - 48
                spacing: Spacing.md

                // Restrained Academic Laurel Illustration
                Image {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 140
                    height: 90
                    source: Assets.laurel_achievement
                    fillMode: Image.PreserveAspectFit
                }

                Column {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 2

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Assessment Complete"
                        color: Theme.deepInk
                        font.pixelSize: Typography.pageTitle
                        font.bold: true
                        font.family: Typography.familyEditorial
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: assessmentController.subject + (assessmentController.chapter.length > 0 ? " • " + assessmentController.chapter : "")
                        color: Theme.mutedInk
                        font.pixelSize: Typography.body
                        font.family: Typography.family
                    }
                }

                // HERO SCORE: 8 / 10 and 80%
                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: Spacing.md

                    Text {
                        text: assessmentController.score + " / " + assessmentController.scoreMax
                        color: Theme.deepInk
                        font.pixelSize: 32
                        font.bold: true
                        font.family: Typography.familyEditorial
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Rectangle {
                        height: 32
                        width: pctText.implicitWidth + 18
                        radius: 16
                        color: Theme.primaryLight
                        border.color: Theme.sage
                        border.width: 1
                        anchors.verticalCenter: parent.verticalCenter

                        Text {
                            id: pctText
                            anchors.centerIn: parent
                            text: assessmentController.scorePercent + "%"
                            color: Theme.forest
                            font.pixelSize: Typography.body
                            font.bold: true
                            font.family: Typography.family
                        }
                    }
                }

                // Performance Breakdown Chips
                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: Spacing.md

                    // Correct chip
                    Rectangle {
                        height: 28
                        width: corrText.implicitWidth + 18
                        radius: 14
                        color: Theme.surfaceSelected
                        border.color: Theme.sage
                        border.width: 1

                        Text {
                            id: corrText
                            anchors.centerIn: parent
                            text: assessmentController.correctCount + " Correct"
                            color: Theme.forest
                            font.pixelSize: Typography.caption
                            font.bold: true
                            font.family: Typography.family
                        }
                    }

                    // Incorrect chip
                    Rectangle {
                        height: 28
                        width: incorrText.implicitWidth + 18
                        radius: 14
                        color: Theme.terracottaLight
                        border.color: Theme.terracotta
                        border.width: 1

                        Text {
                            id: incorrText
                            anchors.centerIn: parent
                            text: assessmentController.wrongCount + " Incorrect"
                            color: Theme.terracotta
                            font.pixelSize: Typography.caption
                            font.bold: true
                            font.family: Typography.family
                        }
                    }

                    // Confidence summary chip
                    Rectangle {
                        height: 28
                        width: confSummaryText.implicitWidth + 18
                        radius: 14
                        color: Theme.surfaceActive
                        border.color: Theme.border
                        border.width: 1

                        Text {
                            id: confSummaryText
                            anchors.centerIn: parent
                            text: (assessmentController.confidenceBreakdown.sure || 0) + " High Confidence"
                            color: Theme.deepInk
                            font.pixelSize: Typography.caption
                            font.bold: true
                            font.family: Typography.family
                        }
                    }
                }

                Item { width: 1; height: Spacing.xs }

                // Actions: Review Answers & Practice Again
                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: Spacing.md

                    PrimaryButton {
                        text: "Review Answers"
                        buttonColor: Theme.forest
                        preferredHeight: Metrics.touchNormal
                        iconSource: Assets.library
                        onClicked: assessmentController.openReview("all")
                    }

                    SecondaryButton {
                        text: "Finish Practice →"
                        preferredHeight: Metrics.touchNormal
                        onClicked: assessmentController.finishAndGoHome()
                    }
                }
            }
        }
    }
}
