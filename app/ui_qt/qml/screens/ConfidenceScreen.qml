import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.background

    Column {
        anchors.centerIn: parent
        spacing: 20
        width: 640

        Column {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 6

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "How confident are you?"
                color: Theme.textPrimary
                font.pixelSize: Theme.fontSizeTitle
                font.bold: true
                font.family: Theme.fontFamily
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Tell us how you feel about your answer."
                color: Theme.textSecondary
                font.pixelSize: Theme.fontSizeSecondary
                font.family: Theme.fontFamily
            }
        }

        // 3 Large Tap Cards
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 16

            // Sure
            AppCard {
                width: 190
                height: 180
                interactive: true
                onClicked: assessmentController.setConfidence("sure")

                Column {
                    anchors.centerIn: parent
                    spacing: 12
                    width: parent.width - 24

                    Rectangle {
                        width: 56
                        height: 56
                        radius: 28
                        color: "#E8F5E9"
                        anchors.horizontalCenter: parent.horizontalCenter

                        Text {
                            anchors.centerIn: parent
                            text: "★"
                            font.pixelSize: 28
                            color: Theme.success
                        }
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "I'm sure"
                        color: Theme.textPrimary
                        font.pixelSize: Theme.fontSizeHeading
                        font.bold: true
                        font.family: Theme.fontFamily
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "I think this is correct."
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontSizeCaption
                        font.family: Theme.fontFamily
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.Wrap
                        width: parent.width
                    }
                }
            }

            // Not sure
            AppCard {
                width: 190
                height: 180
                interactive: true
                onClicked: assessmentController.setConfidence("not_sure")

                Column {
                    anchors.centerIn: parent
                    spacing: 12
                    width: parent.width - 24

                    Rectangle {
                        width: 56
                        height: 56
                        radius: 28
                        color: "#FFF3E0"
                        anchors.horizontalCenter: parent.horizontalCenter

                        Text {
                            anchors.centerIn: parent
                            text: "●"
                            font.pixelSize: 24
                            color: "#E67E22"
                        }
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Not sure"
                        color: Theme.textPrimary
                        font.pixelSize: Theme.fontSizeHeading
                        font.bold: true
                        font.family: Theme.fontFamily
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "I wasn't completely sure."
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontSizeCaption
                        font.family: Theme.fontFamily
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.Wrap
                        width: parent.width
                    }
                }
            }

            // Guessing
            AppCard {
                width: 190
                height: 180
                interactive: true
                onClicked: assessmentController.setConfidence("guessing")

                Column {
                    anchors.centerIn: parent
                    spacing: 12
                    width: parent.width - 24

                    Rectangle {
                        width: 56
                        height: 56
                        radius: 28
                        color: "#FFEBEE"
                        anchors.horizontalCenter: parent.horizontalCenter

                        Text {
                            anchors.centerIn: parent
                            text: "?"
                            font.pixelSize: 28
                            font.bold: true
                            color: Theme.warning
                        }
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "I was guessing"
                        color: Theme.textPrimary
                        font.pixelSize: Theme.fontSizeHeading
                        font.bold: true
                        font.family: Theme.fontFamily
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "I chose without knowing."
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontSizeCaption
                        font.family: Theme.fontFamily
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.Wrap
                        width: parent.width
                    }
                }
            }
        }

        Item { width: 1; height: 4 }

        SecondaryButton {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Skip Rating →"
            preferredHeight: 46
            onClicked: assessmentController.setConfidence("unrated")
        }
    }
}
