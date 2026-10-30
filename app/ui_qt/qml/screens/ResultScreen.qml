import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.background

    Column {
        anchors.centerIn: parent
        spacing: 16
        width: 640

        AppCard {
            width: parent.width
            implicitHeight: contentCol.implicitHeight + 40

            Column {
                id: contentCol
                anchors.centerIn: parent
                width: parent.width - 48
                spacing: 14

                // Header badge
                Rectangle {
                    width: 52
                    height: 52
                    radius: 26
                    color: "#E8F5E9"
                    anchors.horizontalCenter: parent.horizontalCenter

                    Text {
                        anchors.centerIn: parent
                        text: "🎉"
                        font.pixelSize: 26
                    }
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "Assessment Complete!"
                    color: Theme.textPrimary
                    font.pixelSize: Theme.fontSizeTitle
                    font.bold: true
                    font.family: Theme.fontFamily
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: assessmentController.subject + (assessmentController.chapter.length > 0 ? " • " + assessmentController.chapter : "")
                    color: Theme.textSecondary
                    font.pixelSize: Theme.fontSizeSecondary
                    font.family: Theme.fontFamily
                }

                // Score pill
                Rectangle {
                    width: 200
                    height: 60
                    radius: 30
                    color: Theme.primaryLight
                    border.color: Theme.primary
                    border.width: 1
                    anchors.horizontalCenter: parent.horizontalCenter

                    Row {
                        anchors.centerIn: parent
                        spacing: 8
                        Text {
                            text: assessmentController.scorePercent + "%"
                            color: Theme.primaryDark
                            font.pixelSize: 28
                            font.bold: true
                        }
                        Text {
                            text: "(" + assessmentController.score + "/" + assessmentController.scoreMax + ")"
                            color: Theme.textSecondary
                            font.pixelSize: 16
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                }

                // Confidence Breakdown
                Rectangle {
                    width: parent.width
                    height: 54
                    radius: 10
                    color: Theme.surfaceActive
                    border.color: Theme.border
                    border.width: 1

                    Row {
                        anchors.centerIn: parent
                        spacing: 24

                        Row {
                            spacing: 6
                            Text { text: "★"; color: Theme.success; font.pixelSize: 16 }
                            Text { text: assessmentController.confidenceBreakdown.sure + " Sure"; font.bold: true; color: Theme.textPrimary; font.pixelSize: 14 }
                        }

                        Rectangle { width: 1; height: 24; color: Theme.divider; anchors.verticalCenter: parent.verticalCenter }

                        Row {
                            spacing: 6
                            Text { text: "●"; color: "#E67E22"; font.pixelSize: 14 }
                            Text { text: assessmentController.confidenceBreakdown.notSure + " Not Sure"; font.bold: true; color: Theme.textPrimary; font.pixelSize: 14 }
                        }

                        Rectangle { width: 1; height: 24; color: Theme.divider; anchors.verticalCenter: parent.verticalCenter }

                        Row {
                            spacing: 6
                            Text { text: "?"; color: Theme.warning; font.pixelSize: 16; font.bold: true }
                            Text { text: assessmentController.confidenceBreakdown.guessing + " Guessing"; font.bold: true; color: Theme.textPrimary; font.pixelSize: 14 }
                        }
                    }
                }

                Item { width: 1; height: 6 }

                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 16

                    SecondaryButton {
                        text: "Review Answers"
                        preferredHeight: Theme.touchNormal
                        iconSource: Assets.library
                        onClicked: assessmentController.openReview("all")
                    }

                    PrimaryButton {
                        text: "Back to Home →"
                        preferredHeight: Theme.touchNormal
                        onClicked: assessmentController.finishAndGoHome()
                    }
                }
            }
        }
    }
}
