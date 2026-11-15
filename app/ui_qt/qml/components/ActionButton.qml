import QtQuick 2.15
import QtQuick.Controls 2.15
import ".."

AbstractButton {
    id: control

    property url iconSource: ""
    property bool emphasized: false
    property int preferredHeight: Metrics.touchNormal
    property color buttonColor: emphasized ? Theme.forest : Theme.surface
    property color pressedColor: emphasized ? Theme.primaryDark : Theme.surfaceActive
    property color textColor: emphasized ? Theme.textOnPrimary : Theme.deepInk
    property color borderColor: emphasized ? Theme.forest : Theme.border

    padding: 0
    implicitHeight: Math.max(Metrics.touchMin, preferredHeight)
    implicitWidth: Math.max(emphasized ? 140 : 130, buttonLabel.implicitWidth + (buttonIcon.visible ? buttonIcon.width + label.spacing : 0) + (emphasized ? 36 : 32))
    focusPolicy: Qt.StrongFocus
    hoverEnabled: true
    opacity: enabled ? 1 : 0.65
    Accessible.name: text
    Keys.onReturnPressed: clicked()
    Keys.onEnterPressed: clicked()

    background: Rectangle {
        radius: Metrics.radiusMedium
        color: !control.enabled && control.emphasized ? Theme.borderLight : control.down ? control.pressedColor : control.hovered && !control.emphasized ? Theme.surfaceElevated : control.buttonColor
        border.color: control.visualFocus || control.hovered ? Theme.borderFocus : control.borderColor
        border.width: control.visualFocus ? Metrics.borderFocus : 1

        Rectangle {
            anchors.fill: parent
            anchors.margins: -3
            radius: parent.radius + 3
            color: "transparent"
            border.color: Theme.borderFocus
            border.width: Metrics.borderFocus
            visible: control.visualFocus
        }
    }

    contentItem: Item {
        Row {
            id: label
            anchors.centerIn: parent
            spacing: Spacing.sm

            Image {
                id: buttonIcon
                width: control.emphasized ? 20 : 18
                height: width
                sourceSize: Qt.size(width, height)
                anchors.verticalCenter: parent.verticalCenter
                visible: control.iconSource.toString().length > 0
                source: control.iconSource
                fillMode: Image.PreserveAspectFit
            }

            Text {
                id: buttonLabel
                width: Math.min(implicitWidth, Math.max(0, control.width - (buttonIcon.visible ? buttonIcon.width + label.spacing : 0) - 16))
                anchors.verticalCenter: parent.verticalCenter
                text: control.text
                textFormat: Text.PlainText
                color: !control.enabled && control.emphasized ? Theme.mutedInk : control.textColor
                elide: Text.ElideRight
                font.pixelSize: Typography.body
                font.bold: control.emphasized
                font.family: Typography.family
            }
        }
    }
}
