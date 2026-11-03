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
        title: "Device Diagnostics & Health"
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

        Row {
            anchors.fill: parent
            spacing: Spacing.md

            // Overall Summary Card
            AppCard {
                width: 270
                height: parent.height

                Column {
                    anchors.fill: parent
                    anchors.margins: Spacing.lg
                    spacing: Spacing.sm

                    Rectangle {
                        width: 44; height: 44; radius: 22
                        color: appController.isOnline ? Theme.surfaceWarm : "#FDF3EE"
                        border.color: appController.isOnline ? Theme.forest : Theme.terracotta
                        border.width: 1
                        anchors.horizontalCenter: parent.horizontalCenter
                        Text {
                            anchors.centerIn: parent
                            text: appController.isOnline ? "✓" : "!"
                            color: appController.isOnline ? Theme.forest : Theme.terracotta
                            font.pixelSize: 22
                            font.bold: true
                        }
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: settingsController.overallHealth
                        color: Theme.textPrimary
                        font.pixelSize: Typography.sectionTitle
                        font.family: Typography.fontSerif
                        font.bold: true
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Hardware, storage, SQLite assessment database, network connectivity, and cloud sync checks."
                        color: Theme.textSecondary
                        font.pixelSize: Typography.caption
                        font.family: Typography.fontFamily
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.Wrap
                        width: parent.width
                        lineHeight: 1.25
                    }

                    Item { width: 1; height: Spacing.xs }

                    PrimaryButton {
                        width: parent.width
                        preferredHeight: Metrics.touchNormal
                        text: "Run Diagnostics"
                        iconSource: Assets.diagnostics
                        onClicked: settingsController.runDiagnostics()
                    }

                    SecondaryButton {
                        width: parent.width
                        preferredHeight: Metrics.touchNormal
                        text: "Export Support Bundle"
                        iconSource: Assets.download
                        onClicked: settingsController.exportSupportBundle()
                    }
                }
            }

            // Diagnostic Section Breakdown
            AppCard {
                width: parent.width - 270 - Spacing.md
                height: parent.height

                ListView {
                    anchors.fill: parent
                    anchors.margins: Spacing.md
                    clip: true
                    spacing: Spacing.xs

                    model: settingsController.diagnosticItems

                    delegate: Rectangle {
                        width: parent.width
                        height: 52
                        radius: Metrics.radiusSm
                        color: Theme.surfaceActive
                        border.color: Theme.border
                        border.width: 1

                        Item {
                            anchors.fill: parent
                            anchors.margins: Spacing.sm

                            Column {
                                anchors.left: parent.left
                                anchors.right: statusBadge.left
                                anchors.rightMargin: Spacing.sm
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 2
                                Text {
                                    text: modelData.name
                                    font.bold: true
                                    font.pixelSize: Typography.metadata
                                    font.family: Typography.fontFamily
                                    color: Theme.textPrimary
                                }
                                Text {
                                    text: modelData.detail
                                    font.pixelSize: Typography.caption
                                    font.family: Typography.fontFamily
                                    color: Theme.textSecondary
                                    elide: Text.ElideRight
                                    width: parent.width
                                }
                            }

                            StatusBadge {
                                id: statusBadge
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
