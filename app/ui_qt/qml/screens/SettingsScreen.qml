import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.canvas

    Row {
        anchors.fill: parent

        NavRail {
            id: rail
            height: parent.height
            currentTab: "settings"
            onTabSelected: function(tab) {
                if (tab === "home") appController.navigate("home");
                else if (tab === "library") appController.navigate("subjects");
                else if (tab === "practice") appController.navigate("content");
                else if (tab === "history") appController.navigate("history");
                else if (tab === "settings") appController.navigate("settings");
            }
        }

        Column {
            width: parent.width - rail.width
            height: parent.height

            AppHeader {
                width: parent.width
                title: "Settings"
                networkText: appController.networkLabel
                syncText: appController.syncLabel
                isOnline: appController.isOnline
                showBack: true
                onBackClicked: appController.navigate("home")
            }

            Item {
                width: parent.width
                height: parent.height - Metrics.headerHeight

                // Single Flat Appliance Ledger Panel
                Rectangle {
                    anchors.fill: parent
                    anchors.margins: Spacing.md
                    radius: Metrics.radiusMedium
                    color: Theme.surface
                    border.color: Theme.border
                    border.width: 1
                    clip: true

                    ListView {
                        anchors.fill: parent
                        clip: true

                        model: [
                            { id: "wifi", title: "Wi-Fi & Network", value: settingsController.isWifiConnected ? settingsController.connectedSsid : "Not connected", icon: Assets.wifi },
                            { id: "sync", title: "Cloud Synchronization", value: settingsController.syncStatusSummary, icon: Assets.sync },
                            { id: "account", title: "Account & Profiles", value: appController.activeProfileName, icon: Assets.account },
                            { id: "content", title: "Content & Storage", value: "Offline Library", icon: Assets.download },
                            { id: "software_update", title: "Software Update", value: settingsController.currentVersion, icon: Assets.update },
                            { id: "device_info", title: "Device & System", value: "Raspberry Pi", icon: Assets.device },
                            { id: "diagnostics", title: "Hardware Diagnostics", value: "Health check", icon: Assets.diagnostics },
                            { id: "about", title: "About Device", value: "Open-source", icon: Assets.info }
                        ]

                        delegate: Rectangle {
                            width: parent.width
                            height: 48
                            color: rowMouse.containsPress ? Theme.surfaceActive : "transparent"

                            // Bottom row divider line
                            Rectangle {
                                anchors.bottom: parent.bottom
                                anchors.left: parent.left
                                anchors.right: parent.right
                                height: 1
                                color: Theme.borderLight
                                visible: index < 7
                            }

                            Row {
                                anchors.left: parent.left
                                anchors.leftMargin: Spacing.lg
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: Spacing.md

                                Image {
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: 18
                                    height: 18
                                    source: modelData.icon
                                    fillMode: Image.PreserveAspectFit
                                }

                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: modelData.title
                                    color: Theme.deepInk
                                    font.pixelSize: Typography.body
                                    font.bold: true
                                    font.family: Typography.fontFamily
                                }
                            }

                            Row {
                                anchors.right: parent.right
                                anchors.rightMargin: Spacing.lg
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: Spacing.sm

                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: modelData.value
                                    color: Theme.mutedInk
                                    font.pixelSize: Typography.caption
                                    font.family: Typography.fontFamily
                                    horizontalAlignment: Text.AlignRight
                                }

                                Image {
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: 14
                                    height: 14
                                    source: Assets.chevron_right
                                }
                            }

                            MouseArea {
                                id: rowMouse
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: appController.navigate(modelData.id)
                            }
                        }
                    }
                }
            }
        }
    }
}
