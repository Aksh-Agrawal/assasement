import QtQuick 2.15
import ".." 1.0

Rectangle {
    id: root

    property bool interactive: false
    property bool selected: false
    property bool highlighted: false
    property color customBorderColor: "transparent"
    property color customBgColor: "transparent"
    signal clicked()

    radius: Theme.cardRadius
    color: {
        if (customBgColor.a > 0) return customBgColor;
        if (selected) return Theme.surfaceWarm;
        if (highlighted) return Theme.surfaceActive;
        if (interactive && mouseArea.containsPress) return Theme.surfaceActive;
        return Theme.surface;
    }

    border.color: {
        if (selected) return Theme.forest;
        if (customBorderColor.a > 0) return customBorderColor;
        if (interactive && mouseArea.containsPress) return Theme.forest;
        return Theme.border;
    }
    border.width: selected ? 2 : 1

    Behavior on color {
        ColorAnimation { duration: Theme.animDuration }
    }
    Behavior on border.color {
        ColorAnimation { duration: Theme.animDuration }
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

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        enabled: root.interactive
        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: root.clicked()
    }
}
