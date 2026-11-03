import QtQuick 2.15
import ".." 1.0

Rectangle {
    id: root

    property string textValue: ""
    property bool isShift: false
    property bool isSymbols: false
    property string title: "Enter Text"
    property bool isPassword: false

    signal submitted(string text)
    signal cancelled()

    focus: visible
    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            root.submitted(root.textValue);
            event.accepted = true;
        } else if (event.key === Qt.Key_Escape) {
            root.cancelled();
            event.accepted = true;
        } else if (event.key === Qt.Key_Backspace) {
            root.textValue = root.textValue.slice(0, -1);
            event.accepted = true;
        } else if (event.text && event.text.length > 0 && event.text.charCodeAt(0) >= 32) {
            root.textValue += event.text;
            event.accepted = true;
        }
    }

    anchors.fill: parent
    color: "#6623302D"

    Rectangle {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 270
        color: Theme.paper
        border.color: Theme.border
        border.width: 1

        Column {
            anchors.fill: parent
            anchors.margins: Spacing.sm
            spacing: 6

            // Header with title and entered text
            Row {
                width: parent.width
                height: 44
                spacing: Spacing.sm

                // Text Display Input Box
                Rectangle {
                    width: parent.width - 170
                    height: 42
                    radius: Metrics.radiusSm
                    color: Theme.surfaceWarm
                    border.color: Theme.border
                    border.width: 1

                    Row {
                        anchors.fill: parent
                        anchors.margins: Spacing.sm
                        spacing: Spacing.xs

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: root.isPassword ? "•".repeat(root.textValue.length) : root.textValue
                            color: Theme.textPrimary
                            font.pixelSize: Typography.body
                            font.bold: true
                            font.family: Typography.fontFamily
                        }

                        // Blinking cursor
                        Rectangle {
                            width: 2
                            height: 20
                            color: Theme.forest
                            anchors.verticalCenter: parent.verticalCenter
                            SequentialAnimation on opacity {
                                loops: Animation.Infinite
                                NumberAnimation { from: 1; to: 0; duration: 500 }
                                NumberAnimation { from: 0; to: 1; duration: 500 }
                            }
                        }
                    }
                }

                SecondaryButton {
                    width: 76
                    preferredHeight: 42
                    text: "Cancel"
                    onClicked: root.cancelled()
                }

                PrimaryButton {
                    width: 76
                    preferredHeight: 42
                    text: "Done"
                    onClicked: root.submitted(root.textValue)
                }
            }

            // Keyboard rows
            Column {
                width: parent.width
                spacing: 4

                // Row 1: Numbers or Symbols
                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 4
                    Repeater {
                        model: root.isSymbols
                            ? ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "="]
                            : ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]
                        delegate: Rectangle {
                            width: root.isSymbols ? 60 : 72
                            height: 44
                            radius: Metrics.radiusSm
                            color: kMouse.containsPress ? Theme.surfaceWarm : Theme.surfaceActive
                            border.color: kMouse.containsPress ? Theme.forest : Theme.border
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: modelData
                                font.pixelSize: 18
                                font.bold: true
                                font.family: Typography.fontFamily
                                color: Theme.textPrimary
                            }
                            MouseArea {
                                id: kMouse
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.textValue += modelData
                            }
                        }
                    }
                }

                // Row 2: QWERTY
                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 4
                    Repeater {
                        model: root.isSymbols
                            ? ["!", "@", "#", "$", "%", "^", "&", "*", "(", ")"]
                            : ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"]
                        delegate: Rectangle {
                            width: 72
                            height: 44
                            radius: Metrics.radiusSm
                            color: kMouse2.containsPress ? Theme.surfaceWarm : Theme.surfaceActive
                            border.color: kMouse2.containsPress ? Theme.forest : Theme.border
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: root.isShift && !root.isSymbols ? modelData.toUpperCase() : modelData
                                font.pixelSize: 18
                                font.bold: true
                                font.family: Typography.fontFamily
                                color: Theme.textPrimary
                            }
                            MouseArea {
                                id: kMouse2
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    var ch = root.isShift && !root.isSymbols ? modelData.toUpperCase() : modelData;
                                    root.textValue += ch;
                                }
                            }
                        }
                    }
                }

                // Row 3: ASDFGHJKL
                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 4
                    Repeater {
                        model: root.isSymbols
                            ? ["~", "`", "_", "+", "{", "}", "[", "]", ":", ";"]
                            : ["a", "s", "d", "f", "g", "h", "j", "k", "l"]
                        delegate: Rectangle {
                            width: 78
                            height: 44
                            radius: Metrics.radiusSm
                            color: kMouse3.containsPress ? Theme.surfaceWarm : Theme.surfaceActive
                            border.color: kMouse3.containsPress ? Theme.forest : Theme.border
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: root.isShift && !root.isSymbols ? modelData.toUpperCase() : modelData
                                font.pixelSize: 18
                                font.bold: true
                                font.family: Typography.fontFamily
                                color: Theme.textPrimary
                            }
                            MouseArea {
                                id: kMouse3
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    var ch = root.isShift && !root.isSymbols ? modelData.toUpperCase() : modelData;
                                    root.textValue += ch;
                                }
                            }
                        }
                    }
                }

                // Row 4: Shift / Space / Backspace / Symbols
                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 5

                    // Shift key
                    Rectangle {
                        width: 72
                        height: 44
                        radius: Metrics.radiusSm
                        color: root.isShift ? Theme.forest : Theme.surfaceActive
                        border.color: Theme.border
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: "⇧"
                            font.pixelSize: 20
                            color: root.isShift ? Theme.paper : Theme.textPrimary
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.isShift = !root.isShift
                        }
                    }

                    // Symbols toggle key
                    Rectangle {
                        width: 72
                        height: 44
                        radius: Metrics.radiusSm
                        color: root.isSymbols ? Theme.forest : Theme.surfaceActive
                        border.color: Theme.border
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: root.isSymbols ? "ABC" : "?123"
                            font.pixelSize: 15
                            font.bold: true
                            font.family: Typography.fontFamily
                            color: root.isSymbols ? Theme.paper : Theme.textPrimary
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.isSymbols = !root.isSymbols
                        }
                    }

                    // Letters z-m or punctuation
                    Repeater {
                        model: root.isSymbols
                            ? ['"', "'", "<", ">", ",", "."]
                            : ["z", "x", "c", "v", "b", "n", "m"]
                        delegate: Rectangle {
                            width: 64
                            height: 44
                            radius: Metrics.radiusSm
                            color: kMouse4.containsPress ? Theme.surfaceWarm : Theme.surfaceActive
                            border.color: kMouse4.containsPress ? Theme.forest : Theme.border
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: root.isShift && !root.isSymbols ? modelData.toUpperCase() : modelData
                                font.pixelSize: 18
                                font.bold: true
                                font.family: Typography.fontFamily
                                color: Theme.textPrimary
                            }
                            MouseArea {
                                id: kMouse4
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    var ch = root.isShift && !root.isSymbols ? modelData.toUpperCase() : modelData;
                                    root.textValue += ch;
                                }
                            }
                        }
                    }

                    // Spacebar
                    Rectangle {
                        width: 140
                        height: 44
                        radius: Metrics.radiusSm
                        color: sMouse.containsPress ? Theme.surfaceWarm : Theme.surfaceActive
                        border.color: sMouse.containsPress ? Theme.forest : Theme.border
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: "Space"
                            font.pixelSize: 15
                            font.family: Typography.fontFamily
                            color: Theme.textSecondary
                        }
                        MouseArea {
                            id: sMouse
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.textValue += " "
                        }
                    }

                    // Backspace
                    Rectangle {
                        width: 72
                        height: 44
                        radius: Metrics.radiusSm
                        color: bMouse.containsPress ? Theme.surfaceWarm : Theme.surfaceActive
                        border.color: bMouse.containsPress ? Theme.forest : Theme.border
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: "⌫"
                            font.pixelSize: 20
                            color: Theme.textPrimary
                        }
                        MouseArea {
                            id: bMouse
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.textValue = root.textValue.slice(0, -1)
                        }
                    }
                }
            }
        }
    }
}
