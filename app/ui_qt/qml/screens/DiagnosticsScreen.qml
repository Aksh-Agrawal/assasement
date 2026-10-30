import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.background

    AppHeader {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        title: "System Diagnostics"
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
        anchors.margins: 14

        Row {
            anchors.fill: parent
            spacing: 14

            // Overall Summary Card
            AppCard {
                width: 260
                height: parent.height

                Column {
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 12

                    Rectangle {
                        width: 48; height: 48; radius: 24
                        color: appController.isOnline ? "#E8F5E9" : "#FFF3E0"
                        anchors.horizontalCenter: parent.horizontalCenter
                        Text {
                            anchors.centerIn: parent
                            text: appController.isOnline ? "✓" : "!"
                            color: appController.isOnline ? Theme.success : Theme.highlight
                            font.pixelSize: 26
                            font.bold: true
                        }
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: settingsController.overallHealth
                        color: Theme.textPrimary
                        font.pixelSize: Theme.fontSizeHeading
                        font.bold: true
                        font.family: Theme.fontFamily
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Hardware, storage, database, internet, and cloud connectivity diagnostics."
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontSizeCaption
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.Wrap
                        width: parent.width
                    }

                    Item { width: 1; height: 10 }

                    PrimaryButton {
                        width: parent.width
                        preferredHeight: Theme.touchNormal
                        text: "Run Diagnostics"
                        iconSource: Assets.diagnostics
                        onClicked: settingsController.runDiagnostics()
                    }

                    SecondaryButton {
                        width: parent.width
                        preferredHeight: Theme.touchNormal
                        text: "Export Bundle"
                        iconSource: Assets.download
                        onClicked: settingsController.exportSupportBundle()
                    }
                }
            }

            // Diagnostic Section Breakdown
            AppCard {
                width: parent.width - 260 - 14
                height: parent.height

                ListView {
                    anchors.fill: parent
                    anchors.margins: 14
                    clip: true
                    spacing: 8

                    model: settingsController.diagnosticItems

                    delegate: Rectangle {
                        width: parent.width
                        height: 52
                        radius: 8
                        color: Theme.surfaceActive
                        border.color: Theme.border
                        border.width: 1

                        Row {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 12

                            Column {
                                width: parent.width - 130
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 2
                                Text { text: modelData.name; font.bold: true; font.pixelSize: 14; color: Theme.textPrimary }
                                Text { text: modelData.detail; font.pixelSize: 11; color: Theme.textSecondary; elide: Text.ElideRight; width: parent.width }
                            }

                            StatusBadge {
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData.status
                                statusType: {
                                    var s = (modelData.status || "").toLowerCase();
                                    if (s === "ok" || s === "connected" || s === "available" || s === "assigned") return "success";
                                    if (s === "not ready" || s === "action required" || s === "checking…") return "warning";
                                    if (s === "failed" || s === "disconnected" || s === "unavailable" || s === "never") return "offline";
                                    return "neutral";
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    readonly property string appConfigUrl: "https://startup-cloud.onrender.com"
}
