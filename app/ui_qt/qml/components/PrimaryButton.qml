import QtQuick 2.15
import ".." 1.0

Rectangle {
    id: root

    property string text: ""
    property url iconSource: ""
    property int preferredHeight: Metrics.touchNormal
    property color buttonColor: Theme.forest
    property color pressedColor: Theme.primaryDark
    property color textColor: Theme.textOnPrimary

    signal clicked()

    implicitHeight: Math.max(Metrics.touchMin, preferredHeight)
    implicitWidth: Math.max(140, contentRow.implicitWidth + 36)
    radius: Metrics.radiusMedium
    color: !enabled ? Theme.borderLight : (mouseArea.containsPress ? pressedColor : buttonColor)
    border.color: !enabled ? Theme.border : (mouseArea.containsPress ? Theme.primaryDark : Theme.forest)
    border.width: 1
    opacity: enabled ? 1.0 : 0.65

    Behavior on color {
        ColorAnimation { duration: Theme.animDuration }
    }

    Row {
        id: contentRow
        anchors.centerIn: parent
        anchors.verticalCenterOffset: mouseArea.containsPress ? 1 : 0
        spacing: Spacing.sm

        Image {
            id: iconImage
            width: 20
            height: 20
            anchors.verticalCenter: parent.verticalCenter
            visible: root.iconSource.toString().length > 0
            source: root.iconSource
            fillMode: Image.PreserveAspectFit
            smooth: true
        }

        Text {
            id: labelText
            anchors.verticalCenter: parent.verticalCenter
            text: root.text
            color: root.textColor
            font.pixelSize: Typography.body
            font.bold: true
            font.family: Typography.family
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
        border.width: Metrics.borderFocus
        visible: root.activeFocus
    }
}
