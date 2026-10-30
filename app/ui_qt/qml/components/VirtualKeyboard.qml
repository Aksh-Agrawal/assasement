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

    anchors.fill: parent
    color: "#802E2E2E"

    AppCard {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 270
        radius: 0
        color: Theme.background
        border.color: Theme.divider

        Column {
            anchors.fill: parent
            anchors.margins: 8
            spacing: 6

            // Header with title and entered text
            Row {
                width: parent.width
                height: 44
                spacing: 8

                // Text Display Input Box
                Rectangle {
                    width: parent.width - 160
                    height: 42
                    radius: 8
                    color: Theme.surface
                    border.color: Theme.borderFocus
                    border.width: 1

                    Row {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 8

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: root.isPassword ? "•".repeat(root.textValue.length) : root.textValue
                            color: Theme.textPrimary
                            font.pixelSize: Theme.fontSizeBody
                            font.bold: true
                            font.family: Theme.fontFamily
                        }

                        // Blinking cursor
                        Rectangle {
                            width: 2
                            height: 20
                            color: Theme.primary
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
                    width: 72
                    preferredHeight: 42
                    text: "Cancel"
                    onClicked: root.cancelled()
                }

                PrimaryButton {
                    width: 72
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
                            radius: 8
                            color: kMouse.containsPress ? Theme.surfaceActive : Theme.surface
                            border.color: Theme.border
                            Text {
                                anchors.centerIn: parent
                                text: modelData
                                font.pixelSize: 18
                                font.bold: true
                                color: Theme.textPrimary
                            }
                            MouseArea {
                                id: kMouse
                                anchors.fill: parent
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
                            radius: 8
                            color: kMouse2.containsPress ? Theme.surfaceActive : Theme.surface
                            border.color: Theme.border
                            Text {
                                anchors.centerIn: parent
                                text: root.isShift && !root.isSymbols ? modelData.toUpperCase() : modelData
                                font.pixelSize: 18
                                font.bold: true
                                color: Theme.textPrimary
                            }
                            MouseArea {
                                id: kMouse2
                                anchors.fill: parent
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
                            radius: 8
                            color: kMouse3.containsPress ? Theme.surfaceActive : Theme.surface
                            border.color: Theme.border
                            Text {
                                anchors.centerIn: parent
                                text: root.isShift && !root.isSymbols ? modelData.toUpperCase() : modelData
                                font.pixelSize: 18
                                font.bold: true
                                color: Theme.textPrimary
                            }
                            MouseArea {
                                id: kMouse3
                                anchors.fill: parent
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
                        radius: 8
                        color: root.isShift ? Theme.primary : Theme.surfaceActive
                        border.color: Theme.border
                        Text {
                            anchors.centerIn: parent
                            text: "⇧"
                            font.pixelSize: 20
                            color: root.isShift ? Theme.textOnPrimary : Theme.textPrimary
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: root.isShift = !root.isShift
                        }
                    }

                    // Symbols toggle key
                    Rectangle {
                        width: 72
                        height: 44
                        radius: 8
                        color: root.isSymbols ? Theme.primary : Theme.surfaceActive
                        border.color: Theme.border
                        Text {
                            anchors.centerIn: parent
                            text: root.isSymbols ? "ABC" : "?123"
                            font.pixelSize: 15
                            font.bold: true
                            color: root.isSymbols ? Theme.textOnPrimary : Theme.textPrimary
                        }
                        MouseArea {
                            anchors.fill: parent
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
                            radius: 8
                            color: kMouse4.containsPress ? Theme.surfaceActive : Theme.surface
                            border.color: Theme.border
                            Text {
                                anchors.centerIn: parent
                                text: root.isShift && !root.isSymbols ? modelData.toUpperCase() : modelData
                                font.pixelSize: 18
                                font.bold: true
                                color: Theme.textPrimary
                            }
                            MouseArea {
                                id: kMouse4
                                anchors.fill: parent
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
                        radius: 8
                        color: sMouse.containsPress ? Theme.surfaceActive : Theme.surface
                        border.color: Theme.border
                        Text {
                            anchors.centerIn: parent
                            text: "Space"
                            font.pixelSize: 15
                            color: Theme.textSecondary
                        }
                        MouseArea {
                            id: sMouse
                            anchors.fill: parent
                            onClicked: root.textValue += " "
                        }
                    }

                    // Backspace
                    Rectangle {
                        width: 72
                        height: 44
                        radius: 8
                        color: bMouse.containsPress ? Theme.surfaceActive : Theme.surfaceActive
                        border.color: Theme.border
                        Text {
                            anchors.centerIn: parent
                            text: "⌫"
                            font.pixelSize: 20
                            color: Theme.textPrimary
                        }
                        MouseArea {
                            id: bMouse
                            anchors.fill: parent
                            onClicked: root.textValue = root.textValue.slice(0, -1)
                        }
                    }
                }
            }
        }
    }
}
