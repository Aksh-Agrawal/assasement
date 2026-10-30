import QtQuick 2.15
import ".." 1.0

Rectangle {
    id: root

    property string text: ""
    property string iconSource: ""
    property int preferredHeight: Theme.touchNormal
    property color textColor: Theme.textPrimary
    property color borderColor: Theme.border

    signal clicked()

    implicitHeight: preferredHeight
    implicitWidth: Math.max(130, contentRow.implicitWidth + 32)
    radius: Theme.buttonRadius
    color: mouseArea.containsPress ? Theme.surfaceActive : Theme.surface
    border.color: mouseArea.containsPress ? Theme.primary : borderColor
    border.width: 1
    opacity: enabled ? 1.0 : 0.6

    Behavior on color {
        ColorAnimation { duration: Theme.animDuration }
    }

    Row {
        id: contentRow
        anchors.centerIn: parent
        spacing: 8

        Image {
            width: 20
            height: 20
            anchors.verticalCenter: parent.verticalCenter
            visible: root.iconSource.length > 0
            source: root.iconSource
            fillMode: Image.PreserveAspectFit
            smooth: true
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.text
            color: root.textColor
            font.pixelSize: Theme.fontSizeSecondary
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
