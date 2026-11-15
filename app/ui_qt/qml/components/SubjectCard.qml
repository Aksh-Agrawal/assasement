import QtQuick 2.15
import QtQuick.Controls 2.15
import ".."

AbstractButton {
    id: control

    required property string subject
    property string chapters: ""
    text: subject
    focusPolicy: Qt.StrongFocus
    hoverEnabled: true
    padding: Spacing.sm
    Accessible.name: "Explore " + subject
    Accessible.description: chapters
    Keys.onReturnPressed: clicked()
    Keys.onEnterPressed: clicked()

    background: Rectangle {
        radius: Metrics.radiusMedium
        color: !control.enabled ? Theme.surface : control.down ? Theme.surfaceActive : control.hovered ? Theme.surfaceElevated : Theme.surface
        border.color: control.visualFocus ? Theme.borderFocus : Theme.border
        border.width: control.visualFocus ? Metrics.borderFocus : 1
    }

    contentItem: Item {
        Rectangle {
            id: emblem
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            width: 40
            height: 40
            radius: Metrics.radiusSm
            color: Theme.subjectLightAccent(control.subject)

            Image {
                anchors.centerIn: parent
                width: 28
                height: 28
                sourceSize: Qt.size(width, height)
                source: Theme.subjectIcon(control.subject)
                fillMode: Image.PreserveAspectFit
            }
        }

        Column {
            anchors.left: emblem.right
            anchors.leftMargin: Spacing.sm
            anchors.right: arrow.left
            anchors.rightMargin: Spacing.xs
            anchors.verticalCenter: parent.verticalCenter
            spacing: Spacing.xs

            Text {
                width: parent.width
                text: control.subject
                textFormat: Text.PlainText
                color: Theme.deepInk
                font.family: Typography.family
                font.pixelSize: Typography.body
                font.bold: true
                elide: Text.ElideRight
            }
            Text {
                width: parent.width
                text: control.chapters
                textFormat: Text.PlainText
                color: Theme.mutedInk
                font.family: Typography.family
                font.pixelSize: Typography.metadata
                elide: Text.ElideRight
                visible: text.length > 0
            }
        }

        Image {
            id: arrow
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            width: 12
            height: 12
            sourceSize: Qt.size(width, height)
            source: Assets.chevron_right
        }
    }
}
