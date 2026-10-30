import QtQuick 2.15
import ".." 1.0

Rectangle {
    id: root

    property string profileName: "Alex"
    property string pin: ""
    property string errorMessage: ""

    signal pinSubmitted(string pin)
    signal cancelled()

    anchors.fill: parent
    color: "#802E2E2E"

    MouseArea {
        anchors.fill: parent
        onClicked: root.cancelled()
    }

    AppCard {
        anchors.centerIn: parent
        width: 380
        implicitHeight: contentCol.implicitHeight + 36

        MouseArea {
            anchors.fill: parent
        }

        Column {
            id: contentCol
            anchors.centerIn: parent
            width: parent.width - 36
            spacing: 12

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Enter PIN for " + root.profileName
                color: Theme.textPrimary
                font.pixelSize: Theme.fontSizeHeading
                font.bold: true
                font.family: Theme.fontFamily
            }

            // PIN Dots / Display
            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 12

                Repeater {
                    model: 4
                    Rectangle {
                        width: 18
                        height: 18
                        radius: 9
                        color: index < root.pin.length ? Theme.primary : Theme.surfaceActive
                        border.color: Theme.border
                        border.width: 1
                    }
                }
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.errorMessage
                color: Theme.error
                font.pixelSize: Theme.fontSizeCaption
                font.family: Theme.fontFamily
                visible: root.errorMessage.length > 0
            }

            // Numeric Grid (0-9)
            Grid {
                anchors.horizontalCenter: parent.horizontalCenter
                columns: 3
                spacing: 8

                Repeater {
                    model: ["1", "2", "3", "4", "5", "6", "7", "8", "9", "Clear", "0", "⌫"]
                    Rectangle {
                        width: 88
                        height: 48
                        radius: 10
                        color: keyArea.containsPress ? Theme.surfaceActive : Theme.surface
                        border.color: Theme.border
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: modelData
                            color: Theme.textPrimary
                            font.pixelSize: Theme.fontSizeHeading
                            font.bold: true
                            font.family: Theme.fontFamily
                        }

                        MouseArea {
                            id: keyArea
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (modelData === "Clear") {
                                    root.pin = ""
                                } else if (modelData === "⌫") {
                                    root.pin = root.pin.slice(0, -1)
                                } else {
                                    if (root.pin.length < 8) {
                                        root.pin += modelData
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Item { width: 1; height: 4 }

            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 12

                SecondaryButton {
                    text: "Cancel"
                    preferredHeight: 46
                    onClicked: root.cancelled()
                }

                PrimaryButton {
                    text: "Unlock"
                    preferredHeight: 46
                    enabled: root.pin.length > 0
                    onClicked: root.pinSubmitted(root.pin)
                }
            }
        }
    }
}
