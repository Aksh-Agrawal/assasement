import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.canvas

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
        anchors.margins: Spacing.md

        Column {
            anchors.fill: parent
            spacing: Spacing.sm

            // Native Device Wi-Fi Status Bar
            Rectangle {
                width: parent.width
                height: 48
                radius: Metrics.radiusMedium
                color: Theme.surface
                border.color: Theme.border
                border.width: 1

                Row {
                    anchors.fill: parent
                    anchors.leftMargin: Spacing.lg
                    anchors.rightMargin: Spacing.lg

                    Row {
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: Spacing.sm

                        Image {
                            anchors.verticalCenter: parent.verticalCenter
                            width: 20
                            height: 20
                            source: settingsController.isWifiConnected ? Assets.wifi : Assets.wifi_off
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: settingsController.isWifiConnected ? ("Connected to " + settingsController.connectedSsid) : "Wi-Fi is On"
                            color: Theme.deepInk
                            font.pixelSize: Typography.body
                            font.bold: true
                            font.family: Typography.family
                        }
                    }

                    // Rescan button
                    SecondaryButton {
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        preferredHeight: 36
                        text: settingsController.isScanning ? "Scanning…" : "Scan"
                        iconSource: Assets.refresh
                        enabled: !settingsController.isScanning
                        onClicked: settingsController.scanWifi()
                    }
                }
            }

            // Available Networks Panel
            Rectangle {
                width: parent.width
                height: parent.height - 58
                radius: Metrics.radiusMedium
                color: Theme.surface
                border.color: Theme.border
                border.width: 1
                clip: true

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
                    title: "No Networks Found"
                    description: "No wireless hotspots found in range. Tap 'Scan' to refresh."
                    actionText: "Scan Again"
                    onActionClicked: settingsController.scanWifi()
                }

                ListView {
                    anchors.fill: parent
                    clip: true
                    visible: settingsController.availableNetworks.length > 0
                    model: settingsController.availableNetworks

                    delegate: Rectangle {
                        width: parent.width
                        height: 50
                        color: netMouse.containsPress ? Theme.surfaceActive : (modelData.connected ? Theme.surfaceSelected : "transparent")

                        // Row bottom divider
                        Rectangle {
                            anchors.bottom: parent.bottom
                            anchors.left: parent.left
                            anchors.right: parent.right
                            height: 1
                            color: Theme.borderLight
                        }

                        Item {
                            anchors.fill: parent
                            anchors.leftMargin: Spacing.lg
                            anchors.rightMargin: Spacing.lg

                            Row {
                                anchors.left: parent.left
                                anchors.right: statusRow.left
                                anchors.rightMargin: Spacing.md
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: Spacing.md

                                Image {
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: 18
                                    height: 18
                                    source: Assets.wifi
                                }

                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: modelData.ssid
                                    color: Theme.deepInk
                                    font.pixelSize: Typography.body
                                    font.bold: modelData.connected
                                    font.family: Typography.family
                                    elide: Text.ElideRight
                                    width: parent.width - 24
                                }
                            }

                            Row {
                                id: statusRow
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: Spacing.sm

                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: modelData.signal + "%"
                                    color: Theme.mutedInk
                                    font.pixelSize: Typography.caption
                                }

                                Image {
                                    visible: modelData.encrypted && !modelData.connected
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: 14
                                    height: 14
                                    source: Assets.lock
                                }

                                Rectangle {
                                    visible: modelData.connected
                                    height: 24
                                    width: connectedText.implicitWidth + 14
                                    radius: 12
                                    color: Theme.surfaceSelected
                                    border.color: Theme.forest
                                    border.width: 1
                                    anchors.verticalCenter: parent.verticalCenter

                                    Text {
                                        id: connectedText
                                        anchors.centerIn: parent
                                        text: "✓ Connected"
                                        color: Theme.forest
                                        font.pixelSize: Typography.caption
                                        font.bold: true
                                    }
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

    Connections {
        target: appController
        function onKeyboardSubmitted(text) {
            if (appController.keyboardTarget === "wifi_password") {
                settingsController.connectWifi(root.selectedSsid, text);
            }
        }
    }
}
