import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.canvas

    Column {
        anchors.centerIn: parent
        spacing: Spacing.lg
        width: 660

        Column {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: Spacing.xs

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "How confident are you?"
                color: Theme.deepInk
                font.pixelSize: Typography.pageTitle
                font.bold: true
                font.family: Typography.familyEditorial
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Reflecting on your answers builds lasting mastery."
                color: Theme.mutedInk
                font.pixelSize: Typography.body
                font.family: Typography.family
            }
        }

        // 3 Tactile Metacognitive Choice Cards
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: Spacing.lg

            // 1. SURE
            AppCard {
                width: 200
                height: 190
                interactive: true
                onClicked: assessmentController.setConfidence("sure")

                Column {
                    anchors.centerIn: parent
                    spacing: Spacing.md
                    width: parent.width - 24

                    Image {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: 54
                        height: 54
                        source: Assets.confidence_sure
                        fillMode: Image.PreserveAspectFit
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Sure"
                        color: Theme.deepInk
                        font.pixelSize: Typography.sectionTitle
                        font.bold: true
                        font.family: Typography.family
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "I knew the answer"
                        color: Theme.mutedInk
                        font.pixelSize: Typography.metadata
                        font.family: Typography.family
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.Wrap
                        width: parent.width
                    }
                }
            }

            // 2. NOT SURE
            AppCard {
                width: 200
                height: 190
                interactive: true
                onClicked: assessmentController.setConfidence("not_sure")

                Column {
                    anchors.centerIn: parent
                    spacing: Spacing.md
                    width: parent.width - 24

                    Image {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: 54
                        height: 54
                        source: Assets.confidence_not_sure
                        fillMode: Image.PreserveAspectFit
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Not sure"
                        color: Theme.deepInk
                        font.pixelSize: Typography.sectionTitle
                        font.bold: true
                        font.family: Typography.family
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "I narrowed it down"
                        color: Theme.mutedInk
                        font.pixelSize: Typography.metadata
                        font.family: Typography.family
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.Wrap
                        width: parent.width
                    }
                }
            }

            // 3. GUESSING
            AppCard {
                width: 200
                height: 190
                interactive: true
                onClicked: assessmentController.setConfidence("guessing")

                Column {
                    anchors.centerIn: parent
                    spacing: Spacing.md
                    width: parent.width - 24

                    Image {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: 54
                        height: 54
                        source: Assets.confidence_guessing
                        fillMode: Image.PreserveAspectFit
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Guessing"
                        color: Theme.deepInk
                        font.pixelSize: Typography.sectionTitle
                        font.bold: true
                        font.family: Typography.family
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "I wasn't sure"
                        color: Theme.mutedInk
                        font.pixelSize: Typography.metadata
                        font.family: Typography.family
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.Wrap
                        width: parent.width
                    }
                }
            }
        }

        Item { width: 1; height: Spacing.xs }

        SecondaryButton {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Skip Rating →"
            preferredHeight: 44
            onClicked: assessmentController.setConfidence("unrated")
        }
    }
}
