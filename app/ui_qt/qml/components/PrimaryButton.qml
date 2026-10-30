import QtQuick 2.15
import ".." 1.0

Rectangle {
    id: root

    property string text: ""
    property string iconSource: ""
    property int preferredHeight: Theme.touchNormal
    property color buttonColor: Theme.primary
    property color pressedColor: Theme.primaryDark
    property color textColor: Theme.textOnPrimary

    signal clicked()

    implicitHeight: preferredHeight
    implicitWidth: Math.max(140, contentRow.implicitWidth + 36)
    radius: Theme.buttonRadius
    color: !enabled ? Theme.border : (mouseArea.containsPress ? pressedColor : buttonColor)
    opacity: enabled ? 1.0 : 0.65

    Behavior on color {
        ColorAnimation { duration: Theme.animDuration }
    }

    Row {
        id: contentRow
        anchors.centerIn: parent
        spacing: 10

        Image {
            id: iconImage
            width: 22
            height: 22
            anchors.verticalCenter: parent.verticalCenter
            visible: root.iconSource.length > 0
            source: root.iconSource
            fillMode: Image.PreserveAspectFit
            smooth: true
        }

        Text {
            id: labelText
            anchors.verticalCenter: parent.verticalCenter
            text: root.text
            color: root.textColor
            font.pixelSize: Theme.fontSizeBody
            font.bold: true
            font.family: Theme.fontFamily
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        enabled: root.enabled
        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: root.clicked()
    }

    // Accessible keyboard focus indicator
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
