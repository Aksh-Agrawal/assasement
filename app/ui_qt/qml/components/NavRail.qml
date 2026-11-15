import QtQuick 2.15
import QtQuick.Controls 2.15
import ".." 1.0

Rectangle {
    id: root

    property string currentTab: "home" // "home", "library", "practice", "progress", "history", "settings"
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
                { id: "progress", label: "Analytics", icon: Assets.analytics },
                { id: "history", label: "History", icon: Assets.history },
                { id: "settings", label: "Settings", icon: Assets.settings }
            ]

            delegate: AbstractButton {
                id: navItem
                required property var modelData
                readonly property bool selected: root.currentTab === modelData.id
                width: root.width - 12
                height: 56
                anchors.horizontalCenter: parent.horizontalCenter
                padding: 0
                text: modelData.label
                Accessible.name: text
                focusPolicy: Qt.StrongFocus
                hoverEnabled: true
                Keys.onReturnPressed: clicked()
                Keys.onEnterPressed: clicked()
                onClicked: root.tabSelected(modelData.id)

                background: Rectangle {
                    radius: Metrics.radiusMedium
                    color: navItem.down ? Theme.surfaceActive : navItem.selected ? Theme.primaryLight
                        : navItem.hovered ? Theme.paper : "transparent"
                    border.color: Theme.borderFocus
                    border.width: navItem.visualFocus ? Metrics.borderFocus : 0

                    Rectangle {
                        anchors.left: parent.left
                        anchors.leftMargin: 3
                        anchors.verticalCenter: parent.verticalCenter
                        width: 3
                        height: 28
                        radius: 1.5
                        color: Theme.forest
                        visible: navItem.selected
                    }
                }

                contentItem: Item {
                    Column {
                        anchors.centerIn: parent
                        spacing: 3

                        Image {
                            objectName: "navIcon-" + navItem.modelData.id
                            anchors.horizontalCenter: parent.horizontalCenter
                            width: 22
                            height: 22
                            sourceSize: Qt.size(width, height)
                            source: navItem.modelData.icon
                            fillMode: Image.PreserveAspectFit
                        }

                        Text {
                            objectName: "navLabel-" + navItem.modelData.id
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: navItem.text
                            color: navItem.selected ? Theme.forest : Theme.mutedInk
                            font.pixelSize: Typography.caption
                            font.bold: navItem.selected
                            font.family: Typography.family
                        }
                    }
                }
            }
        }
    }
}
