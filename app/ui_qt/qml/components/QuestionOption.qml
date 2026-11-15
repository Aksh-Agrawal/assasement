import QtQuick 2.15
import QtQuick.Controls 2.15
import ".." 1.0

AbstractButton {
    id: root

    property string optionKey: "A"
    property string optionText: ""
    property bool selected: false
    padding: 0
    focusPolicy: Qt.StrongFocus
    hoverEnabled: true
    Accessible.name: optionKey + ". " + optionText
    Accessible.selected: selected
    Keys.onReturnPressed: clicked()
    Keys.onEnterPressed: clicked()
    implicitHeight: Math.max(Metrics.touchNormal, textLayout.implicitHeight + 18)
    opacity: enabled ? 1.0 : 0.6

    background: Rectangle {
        radius: Metrics.radiusMedium
        color: root.selected ? Theme.surfaceSelected
            : root.down ? Theme.surfaceActive : root.hovered ? Theme.surfaceElevated : Theme.surface
        border.color: root.selected || root.visualFocus ? Theme.forest : Theme.border
        border.width: root.selected || root.visualFocus ? Metrics.borderFocus : 1

        Behavior on color {
            ColorAnimation { duration: Theme.animDuration }
        }
    }

    Row {
        id: textLayout
        anchors.fill: parent
        anchors.leftMargin: Spacing.md
        anchors.rightMargin: Spacing.md
        anchors.topMargin: Spacing.sm
        anchors.bottomMargin: Spacing.sm
        spacing: Spacing.md

        // Option Key Disc (e.g. "A")
        Rectangle {
            width: 36
            height: 36
            radius: 18
            anchors.verticalCenter: parent.verticalCenter
            color: root.selected ? Theme.forest : Theme.surfaceActive
            border.color: root.selected ? Theme.primaryDark : Theme.border
            border.width: 1

            Text {
                anchors.centerIn: parent
                text: root.optionKey
                color: root.selected ? Theme.textOnPrimary : Theme.deepInk
                font.pixelSize: Typography.sectionTitle
                font.bold: true
                font.family: Typography.family
            }
        }

        // Option Text (Wrap correctly without ellipsis truncation)
        Text {
            id: contentText
            width: parent.width - 36 - Spacing.md - (root.selected ? 34 : 0)
            anchors.verticalCenter: parent.verticalCenter
            text: root.optionText
            textFormat: Text.PlainText
            color: Theme.deepInk
            font.pixelSize: Typography.body
            font.family: Typography.family
            wrapMode: Text.Wrap
        }

        // Selected Checkmark indicator (non-color indicator!)
        Rectangle {
            width: 26
            height: 26
            radius: 13
            anchors.verticalCenter: parent.verticalCenter
            color: Theme.forest
            visible: root.selected

            Image {
                anchors.centerIn: parent
                width: 14
                height: 14
                source: Assets.check
                fillMode: Image.PreserveAspectFit
            }
        }
    }

}
