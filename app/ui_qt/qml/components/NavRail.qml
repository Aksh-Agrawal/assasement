import QtQuick 2.15
import ".." 1.0

Rectangle {
    id: root

    property string currentTab: "home" // "home", "library", "practice", "history", "settings"
    signal tabSelected(string tab)

    width: Theme.navRailWidth
    color: Theme.surface
    border.color: Theme.border
    border.width: 1

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
        anchors.topMargin: 12
        anchors.bottomMargin: 12
        spacing: 8

        // Mini device mark at top
        Rectangle {
            width: 44
            height: 44
            radius: 22
            color: Theme.primaryLight
            anchors.horizontalCenter: parent.horizontalCenter

            Image {
                anchors.centerIn: parent
                width: 24
                height: 24
                source: Assets.raspberry
                fillMode: Image.PreserveAspectFit
            }
        }

        Item { width: 1; height: 8 }

        Repeater {
            model: [
                { id: "home", label: "Home", icon: Assets.home },
                { id: "library", label: "Library", icon: Assets.library },
                { id: "practice", label: "Practice", icon: Assets.practice },
                { id: "history", label: "History", icon: Assets.history },
                { id: "settings", label: "Settings", icon: Assets.settings }
            ]

            delegate: Rectangle {
                id: navItem
                width: root.width - 16
                height: 60
                anchors.horizontalCenter: parent.horizontalCenter
                radius: 12
                color: root.currentTab === modelData.id ? Theme.primaryLight : (itemMouseArea.containsPress ? Theme.surfaceActive : "transparent")

                border.color: root.currentTab === modelData.id ? Theme.primary : "transparent"
                border.width: root.currentTab === modelData.id ? 1 : 0

                Behavior on color {
                    ColorAnimation { duration: Theme.animDuration }
                }

                Column {
                    anchors.centerIn: parent
                    spacing: 4

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
                        color: root.currentTab === modelData.id ? Theme.primaryDark : Theme.textSecondary
                        font.pixelSize: Theme.fontSizeCaption
                        font.bold: root.currentTab === modelData.id
                        font.family: Theme.fontFamily
                    }
                }

                MouseArea {
                    id: itemMouseArea
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.tabSelected(modelData.id)
                }
            }
        }
    }
}
