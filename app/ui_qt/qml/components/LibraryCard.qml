import QtQuick 2.15
import QtQuick.Controls 2.15
import ".." 1.0

AbstractButton {
    id: root

    property string title: ""
    property string context: ""
    property string status: ""
    property string actionText: ""
    property url iconSource: ""
    property bool ready: false

    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    Accessible.name: [title, status, actionText].filter(function(value) { return value.length > 0; }).join(", ")
    Keys.onReturnPressed: clicked()

    background: AppCard {
        highlighted: root.hovered || root.down
        customBorderColor: root.activeFocus ? Theme.borderFocus : "transparent"
    }

    contentItem: Item {
        Column {
            anchors.fill: parent
            anchors.margins: Spacing.md
            spacing: Spacing.xs

            Item {
                width: parent.width
                height: heading.implicitHeight

                Image {
                    id: icon
                    width: 30
                    height: 30
                    anchors.verticalCenter: parent.verticalCenter
                    source: root.iconSource
                    visible: root.iconSource.toString().length > 0
                    fillMode: Image.PreserveAspectFit
                }

                Text {
                    id: heading
                    anchors.left: icon.visible ? icon.right : parent.left
                    anchors.leftMargin: icon.visible ? Spacing.sm : 0
                    anchors.right: parent.right
                    text: root.title
                    color: Theme.deepInk
                    font.family: Typography.fontFamily
                    font.pixelSize: Typography.body
                    font.bold: true
                    textFormat: Text.PlainText
                    wrapMode: Text.Wrap
                    maximumLineCount: 3
                    elide: Text.ElideRight
                }
            }

            Text {
                width: parent.width
                text: root.context
                textFormat: Text.PlainText
                color: Theme.mutedInk
                font.family: Typography.fontFamily
                font.pixelSize: Typography.caption
                elide: Text.ElideRight
                visible: text.length > 0
            }
        }

        Row {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: Spacing.md
            spacing: Spacing.sm

            Text {
                width: parent.width - actionLabel.implicitWidth - parent.spacing
                text: root.status
                color: root.ready ? Theme.forest : Theme.mutedInk
                font.family: Typography.fontFamily
                font.pixelSize: Typography.caption
                elide: Text.ElideRight
            }

            Text {
                id: actionLabel
                text: root.actionText
                color: Theme.forest
                font.family: Typography.fontFamily
                font.pixelSize: Typography.caption
                font.bold: true
            }
        }
    }
}
