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
        title: "Device Specifications"
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

        AppCard {
            anchors.centerIn: parent
            width: 580
            implicitHeight: contentCol.implicitHeight + Spacing.xl * 2

            Column {
                id: contentCol
                anchors.centerIn: parent
                width: parent.width - Spacing.xl * 2
                spacing: Spacing.md

                Row {
                    spacing: Spacing.sm
                    Rectangle {
                        width: 32; height: 32; radius: 16
                        color: Theme.primaryLight
                        Image {
                            anchors.centerIn: parent
                            width: 18; height: 18
                            source: Assets.raspberry
                            fillMode: Image.PreserveAspectFit
                        }
                    }
                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        Text {
                            text: "About this device"
                            color: Theme.textPrimary
                            font.pixelSize: Typography.sectionTitle
                            font.family: Typography.fontSerif
                            font.bold: true
                        }
                    }
                }

                Grid {
                    width: parent.width
                    columns: 2
                    rowSpacing: Spacing.sm
                    columnSpacing: Spacing.lg
                    readonly property real fieldWidth: (width - columnSpacing) / columns

                    Column {
                        width: parent.fieldWidth
                        spacing: 2
                        Text { text: "Device Identity"; color: Theme.textSecondary; font.pixelSize: Typography.caption; font.family: Typography.fontFamily }
                        Text { text: "Questraa"; font.bold: true; color: Theme.textPrimary; font.pixelSize: Typography.body; font.family: Typography.fontFamily }
                    }

                    Column {
                        width: parent.fieldWidth
                        spacing: 2
                        Text { text: "Hardware Platform"; color: Theme.textSecondary; font.pixelSize: Typography.caption; font.family: Typography.fontFamily }
                        Text { width: parent.width; wrapMode: Text.Wrap; text: "Raspberry Pi Zero 2 W (512 MB)"; font.bold: true; color: Theme.textPrimary; font.pixelSize: Typography.body; font.family: Typography.fontFamily }
                    }

                    Column {
                        width: parent.fieldWidth
                        spacing: 2
                        Text { text: "Display Resolution"; color: Theme.textSecondary; font.pixelSize: Typography.caption; font.family: Typography.fontFamily }
                        Text { text: "800 × 480 landscape"; font.bold: true; color: Theme.textPrimary; font.pixelSize: Typography.body; font.family: Typography.fontFamily }
                    }

                    Column {
                        width: parent.fieldWidth
                        spacing: 2
                        Text { text: "Software Release"; color: Theme.textSecondary; font.pixelSize: Typography.caption; font.family: Typography.fontFamily }
                        Text { text: "v" + settingsController.appVersion; font.bold: true; color: Theme.textPrimary; font.pixelSize: Typography.body; font.family: Typography.fontFamily }
                    }

                    Column {
                        width: parent.fieldWidth
                        spacing: 2
                        Text { text: "Device Identifier"; color: Theme.textSecondary; font.pixelSize: Typography.caption; font.family: Typography.fontFamily }
                        Text { text: settingsController.deviceId; font.bold: true; color: Theme.textPrimary; font.pixelSize: Typography.metadata; font.family: Typography.fontFamily; elide: Text.ElideRight; width: parent.width }
                    }

                    Column {
                        width: parent.fieldWidth
                        spacing: 2
                        Text { text: "Local Storage"; color: Theme.textSecondary; font.pixelSize: Typography.caption; font.family: Typography.fontFamily }
                        Text { text: settingsController.storageUsedGb + " GB / " + settingsController.storageTotalGb + " GB"; font.bold: true; color: Theme.textPrimary; font.pixelSize: Typography.body; font.family: Typography.fontFamily }
                    }
                }
            }
        }
    }
}
