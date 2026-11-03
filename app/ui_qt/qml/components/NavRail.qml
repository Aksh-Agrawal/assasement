import QtQuick 2.15
import ".." 1.0

Rectangle {
    id: root

    property string currentTab: "home" // "home", "library", "practice", "history", "settings"
    signal tabSelected(string tab)

    width: Metrics.navRailWidth
    color: Theme.surface

    // Right-edge divider line
    Rectangle {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 1
        color: Theme.divider
    }

    Column {
        anchors.fill: parent
        anchors.topMargin: Spacing.sm
        anchors.bottomMargin: Spacing.sm
        spacing: 6

        // Educational emblem at top
        Rectangle {
            width: 42
            height: 42
            radius: 21
            color: Theme.primaryLight
            border.color: Theme.sage
            border.width: 1
            anchors.horizontalCenter: parent.horizontalCenter

            Image {
                anchors.centerIn: parent
                width: 24
                height: 24
                source: Assets.raspberry
                fillMode: Image.PreserveAspectFit
            }
        }

        Item { width: 1; height: 4 }

        Repeater {
            model: [
                { id: "home", label: "Home", icon: Assets.home },
                { id: "library", label: "Library", icon: Assets.library },
                { id: "practice", label: "Practice", icon: Assets.practice },
                { id: "history", label: "Progress", icon: Assets.history },
                { id: "settings", label: "Settings", icon: Assets.settings }
            ]

            delegate: Rectangle {
                id: navItem
                width: root.width - 12
                height: 56
                anchors.horizontalCenter: parent.horizontalCenter
                radius: Metrics.radiusMedium
                color: root.currentTab === modelData.id ? Theme.primaryLight : (itemMouseArea.containsPress ? Theme.surfaceActive : "transparent")

                Behavior on color {
                    ColorAnimation { duration: Theme.animDuration }
                }

                // Left active accent bar
                Rectangle {
                    anchors.left: parent.left
                    anchors.leftMargin: 2
                    anchors.verticalCenter: parent.verticalCenter
                    width: 3
                    height: 28
                    radius: 1.5
                    color: Theme.forest
                    visible: root.currentTab === modelData.id
                }

                Column {
                    anchors.centerIn: parent
                    spacing: 3

                    Image {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: 22
                        height: 22
                        source: modelData.icon
                        fillMode: Image.PreserveAspectFit
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: modelData.label
                        color: root.currentTab === modelData.id ? Theme.forest : Theme.mutedInk
                        font.pixelSize: Typography.caption
                        font.bold: root.currentTab === modelData.id
                        font.family: Typography.family
                    }
                }

                MouseArea {
                    id: itemMouseArea
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.tabSelected(modelData.id)
                }

                // Focus ring
                Rectangle {
                    anchors.fill: parent
                    anchors.margins: -2
                    radius: navItem.radius + 2
                    color: "transparent"
                    border.color: Theme.borderFocus
                    border.width: Metrics.borderFocus
                    visible: navItem.activeFocus
                }
            }
        }
    }
}
