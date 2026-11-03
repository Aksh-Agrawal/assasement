import QtQuick 2.15
import ".." 1.0

Rectangle {
    id: root

    property string profileName: "Student"
    property string pin: ""
    property string errorMessage: ""

    signal pinSubmitted(string pin)
    signal cancelled()

    anchors.fill: parent
    color: "#6623302D"

    MouseArea {
        anchors.fill: parent
        onClicked: root.cancelled()
    }

    AppCard {
        anchors.centerIn: parent
        width: 380
        implicitHeight: contentCol.implicitHeight + Spacing.xl * 2

        MouseArea {
            anchors.fill: parent
        }

        Column {
            id: contentCol
            anchors.centerIn: parent
            width: parent.width - Spacing.xl * 2
            spacing: Spacing.md

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Enter PIN for " + root.profileName
                color: Theme.textPrimary
                font.pixelSize: Typography.sectionTitle
                font.family: Typography.fontSerif
                font.bold: true
            }

            // PIN Dots / Display
            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: Spacing.md

                Repeater {
                    model: 4
                    Rectangle {
                        width: 18
                        height: 18
                        radius: 9
                        color: index < root.pin.length ? Theme.forest : Theme.surfaceActive
                        border.color: index < root.pin.length ? Theme.forest : Theme.border
                        border.width: 1
                    }
                }
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.errorMessage
                color: Theme.terracotta
                font.pixelSize: Typography.caption
                font.family: Typography.fontFamily
                visible: root.errorMessage.length > 0
            }

            // Numeric Grid (0-9)
            Grid {
                anchors.horizontalCenter: parent.horizontalCenter
                columns: 3
                spacing: Spacing.xs

                Repeater {
                    model: ["1", "2", "3", "4", "5", "6", "7", "8", "9", "Clear", "0", "⌫"]
                    Rectangle {
                        width: 90
                        height: Metrics.touchNormal
                        radius: Metrics.radiusSm
                        color: keyArea.containsPress ? Theme.surfaceWarm : Theme.surfaceActive
                        border.color: keyArea.containsPress ? Theme.forest : Theme.border
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: modelData
                            color: Theme.textPrimary
                            font.pixelSize: modelData.length > 1 ? Typography.body : Typography.sectionTitle
                            font.bold: true
                            font.family: Typography.fontFamily
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

            Item { width: 1; height: Spacing.xs }

            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: Spacing.md

                SecondaryButton {
                    text: "Cancel"
                    preferredHeight: Metrics.touchNormal
                    onClicked: root.cancelled()
                }

                PrimaryButton {
                    text: "Unlock"
                    preferredHeight: Metrics.touchNormal
                    enabled: root.pin.length > 0
                    onClicked: root.pinSubmitted(root.pin)
                }
            }
        }
    }
}
