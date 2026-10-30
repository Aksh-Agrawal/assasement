import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.background

    property string selectedSsid: ""
    property string wifiPassword: ""

    AppHeader {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        title: "Wi-Fi & Network"
        networkText: appController.networkLabel
        syncText: appController.syncLabel
        isOnline: appController.isOnline
        showBack: true
        onBackClicked: appController.navigate("settings")
    }

    Item {
        anchors.top: header.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 16

        Row {
            anchors.fill: parent
            spacing: 16

            // LEFT PANEL: Connectivity Status Card
            AppCard {
                width: 300
                height: parent.height

                Column {
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 12

                    Text {
                        text: "Connection Status"
                        color: Theme.textPrimary
                        font.pixelSize: Theme.fontSizeHeading
                        font.bold: true
                        font.family: Theme.fontFamily
                    }

                    // Wi-Fi Status
                    Column {
                        spacing: 2
                        Text { text: "Wi-Fi Network"; color: Theme.textSecondary; font.pixelSize: 13 }
                        Row {
                            spacing: 6
                            StatusBadge {
                                text: settingsController.isConnecting ? "Connecting…" : (settingsController.isWifiConnected ? "Connected" : "Disconnected")
                                statusType: settingsController.isConnecting ? "syncing" : (settingsController.isWifiConnected ? "online" : "offline")
                            }
                            Text {
                                text: settingsController.connectedSsid
                                color: Theme.textPrimary
                                font.pixelSize: 14
                                font.bold: true
                                elide: Text.ElideRight
                                width: 140
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }
                    }

                    Rectangle { width: parent.width; height: 1; color: Theme.divider }

                    // Internet Status
                    Column {
                        spacing: 2
                        Text { text: "Internet Reachability"; color: Theme.textSecondary; font.pixelSize: 13 }
                        StatusBadge {
                            text: settingsController.internetStatus
                            statusType: settingsController.internetStatus === "Available" ? "success" : (settingsController.internetStatus === "Checking…" ? "neutral" : "offline")
                        }
                    }

                    Rectangle { width: parent.width; height: 1; color: Theme.divider }

                    // Cloud Server Status
                    Column {
                        spacing: 2
                        Text { text: "Study Buddy Cloud"; color: Theme.textSecondary; font.pixelSize: 13 }
                        StatusBadge {
                            text: settingsController.cloudStatus
                            statusType: settingsController.cloudStatus === "Online" ? "success" : (settingsController.cloudStatus === "Server unavailable" || settingsController.cloudStatus === "Authentication required" ? "warning" : (settingsController.cloudStatus === "Checking…" ? "neutral" : "offline"))
                        }
                    }

                    Item { width: 1; height: 12 }

                    PrimaryButton {
                        width: parent.width
                        preferredHeight: Theme.touchNormal
                        text: settingsController.isScanning ? "Scanning…" : "Scan Networks"
                        iconSource: Assets.refresh
                        enabled: !settingsController.isScanning
                        onClicked: settingsController.scanWifi()
                    }
                }
            }

            // RIGHT PANEL: Available Networks List
            AppCard {
                width: parent.width - 300 - 16
                height: parent.height

                Column {
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 10

                    Row {
                        width: parent.width
                        Text {
                            text: "Available Networks"
                            color: Theme.textPrimary
                            font.pixelSize: Theme.fontSizeHeading
                            font.bold: true
                            font.family: Theme.fontFamily
                        }
                    }

                    // Scanning State
                    LoadingState {
                        anchors.centerIn: parent
                        visible: settingsController.isScanning && settingsController.availableNetworks.length === 0
                        message: "Scanning for wireless networks…"
                    }

                    // Empty / Scan Failed State
                    EmptyState {
                        anchors.centerIn: parent
                        visible: !settingsController.isScanning && settingsController.availableNetworks.length === 0
                        title: "No Wi-Fi Networks Found"
                        description: "Couldn’t find wireless networks in range. Tap 'Retry' to rescan."
                        actionText: "Retry Scan"
                        onActionClicked: settingsController.scanWifi()
                    }

                    ListView {
                        width: parent.width
                        height: parent.height - 40
                        clip: true
                        spacing: 6
                        visible: settingsController.availableNetworks.length > 0
                        model: settingsController.availableNetworks

                        delegate: Rectangle {
                            width: parent.width
                            height: 52
                            radius: 8
                            color: netMouse.containsPress ? Theme.surfaceActive : Theme.surface
                            border.color: modelData.connected ? Theme.primary : Theme.border
                            border.width: modelData.connected ? 2 : 1

                            Item {
                                anchors.fill: parent
                                anchors.leftMargin: 12
                                anchors.rightMargin: 12

                                Row {
                                    anchors.left: parent.left
                                    anchors.right: statusBadgeRow.left
                                    anchors.rightMargin: 8
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 10

                                    Image {
                                        anchors.verticalCenter: parent.verticalCenter
                                        width: 20
                                        height: 20
                                        source: Assets.wifi
                                    }

                                    Text {
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: modelData.ssid
                                        color: Theme.textPrimary
                                        font.pixelSize: 15
                                        font.bold: modelData.connected
                                        elide: Text.ElideRight
                                        width: parent.width - 80
                                    }
                                }

                                Row {
                                    id: statusBadgeRow
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 8

                                    Text {
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: modelData.signal + "%"
                                        color: Theme.textSecondary
                                        font.pixelSize: 12
                                    }

                                    StatusBadge {
                                        visible: modelData.connected
                                        text: "Connected"
                                        statusType: "online"
                                    }

                                    StatusBadge {
                                        visible: modelData.saved && !modelData.connected
                                        text: "Saved"
                                        statusType: "neutral"
                                    }

                                    Image {
                                        visible: modelData.encrypted && !modelData.connected
                                        anchors.verticalCenter: parent.verticalCenter
                                        width: 16
                                        height: 16
                                        source: Assets.lock
                                    }
                                }
                            }

                            MouseArea {
                                id: netMouse
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    if (!modelData.connected) {
                                        root.selectedSsid = modelData.ssid;
                                        if (modelData.saved || !modelData.encrypted) {
                                            // Saved network or open hotspot: connect directly without password prompt
                                            settingsController.connectWifi(modelData.ssid, "");
                                        } else {
                                            appController.openKeyboard("wifi_password", "", true, "Enter Password for " + modelData.ssid);
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Connections {
        target: appController
        function onKeyboardSubmitted(text) {
            if (appController.keyboardTarget === "wifi_password") {
                settingsController.connectWifi(root.selectedSsid, text);
            }
        }
    }
}
