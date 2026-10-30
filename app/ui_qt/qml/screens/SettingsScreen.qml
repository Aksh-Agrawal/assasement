import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.background

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

            ListView {
                width: parent.width
                height: parent.height - Theme.headerHeight
                clip: true
                spacing: 8
                topMargin: 8
                bottomMargin: 16

                model: [
                    { id: "wifi", title: "Wi-Fi / Network", desc: "Connect to the internet and networks", icon: Assets.wifi },
                    { id: "sync", title: "Sync", desc: "Sync progress and assessments with cloud", icon: Assets.sync },
                    { id: "account", title: "Account & Profiles", desc: "Manage device pairing and study profiles", icon: Assets.account },
                    { id: "content", title: "Content & Downloads", desc: "Installed packs and storage space", icon: Assets.download },
                    { id: "software_update", title: "Software Update", desc: "System updates and version checks", icon: Assets.update },
                    { id: "device_info", title: "Device & System", desc: "Hardware and OS status", icon: Assets.device },
                    { id: "diagnostics", title: "Diagnostics", desc: "Check hardware, database and API health", icon: Assets.diagnostics },
                    { id: "about", title: "About", desc: "App version and device license info", icon: Assets.info }
                ]

                delegate: Item {
                    width: parent.width
                    height: 58

                    AppCard {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: parent.width - 32
                        height: 54
                        interactive: true
                        onClicked: appController.navigate(modelData.id)

                        Row {
                            anchors.fill: parent
                            anchors.leftMargin: 16
                            anchors.rightMargin: 16
                            spacing: 14

                            Rectangle {
                                width: 36
                                height: 36
                                radius: 10
                                color: Theme.surfaceActive
                                anchors.verticalCenter: parent.verticalCenter

                                Image {
                                    anchors.centerIn: parent
                                    width: 20
                                    height: 20
                                    source: modelData.icon
                                    fillMode: Image.PreserveAspectFit
                                }
                            }

                            Column {
                                width: parent.width - 36 - 14 - 40
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 2

                                Text {
                                    text: modelData.title
                                    color: Theme.textPrimary
                                    font.pixelSize: Theme.fontSizeBody
                                    font.bold: true
                                    font.family: Theme.fontFamily
                                }

                                Text {
                                    text: modelData.desc
                                    color: Theme.textSecondary
                                    font.pixelSize: Theme.fontSizeCaption
                                    font.family: Theme.fontFamily
                                }
                            }

                            Image {
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                width: 18
                                height: 18
                                source: Assets.chevron_right
                            }
                        }
                    }
                }
            }
        }
    }
}
