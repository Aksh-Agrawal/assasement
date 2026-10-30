import QtQuick 2.15
import ".." 1.0

Rectangle {
    id: root

    property string optionKey: "A"
    property string optionText: ""
    property bool selected: false
    signal clicked()

    implicitHeight: Math.max(Theme.touchLarge, textLayout.implicitHeight + 20)
    radius: Theme.cardRadius
    color: selected ? Theme.surfaceSelected : (mouseArea.containsPress ? Theme.surfaceActive : Theme.surface)
    border.color: selected ? Theme.primary : Theme.border
    border.width: selected ? 2 : 1
    opacity: enabled ? 1.0 : 0.6

    Behavior on color {
        ColorAnimation { duration: Theme.animDuration }
    }
    Behavior on border.color {
        ColorAnimation { duration: Theme.animDuration }
    }

    Row {
        id: textLayout
        anchors.fill: parent
        anchors.margins: 12
        spacing: 14

        // Option Key Badge (e.g. "A")
        Rectangle {
            width: 38
            height: 38
            radius: 19
            anchors.verticalCenter: parent.verticalCenter
            color: root.selected ? Theme.primary : Theme.surfaceActive
            border.color: root.selected ? Theme.primaryDark : Theme.border
            border.width: 1

            Text {
                anchors.centerIn: parent
                text: root.optionKey
                color: root.selected ? Theme.textOnPrimary : Theme.textPrimary
                font.pixelSize: Theme.fontSizeHeading
                font.bold: true
                font.family: Theme.fontFamily
            }
        }

        // Option Text
        Text {
            id: contentText
            width: parent.width - 38 - 14 - (root.selected ? 36 : 0)
            anchors.verticalCenter: parent.verticalCenter
            text: root.optionText
            color: Theme.textPrimary
            font.pixelSize: Theme.fontSizeBody
            font.family: Theme.fontFamily
            wrapMode: Text.Wrap
            maximumLineCount: 3
            elide: Text.ElideRight
        }

        // Selected Checkmark indicator (non-color indicator!)
        Rectangle {
            width: 28
            height: 28
            radius: 14
            anchors.verticalCenter: parent.verticalCenter
            color: Theme.primary
            visible: root.selected

            Text {
                anchors.centerIn: parent
                text: "✓"
                color: Theme.textOnPrimary
                font.pixelSize: 16
                font.bold: true
            }
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        enabled: root.enabled
        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: root.clicked()
    }

    // Accessible keyboard focus ring
    Rectangle {
        anchors.fill: parent
        anchors.margins: -3
        radius: root.radius + 3
        color: "transparent"
        border.color: Theme.borderFocus
        border.width: 2
        visible: root.activeFocus
    }
}
