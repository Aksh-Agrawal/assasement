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
        title: "Device & System Info"
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

        AppCard {
            anchors.centerIn: parent
            width: 580
            implicitHeight: contentCol.implicitHeight + 40

            Column {
                id: contentCol
                anchors.centerIn: parent
                width: parent.width - 48
                spacing: 14

                Text {
                    text: "Device Specifications"
                    color: Theme.textPrimary
                    font.pixelSize: Theme.fontSizeHeading
                    font.bold: true
                    font.family: Theme.fontFamily
                }

                Grid {
                    width: parent.width
                    columns: 2
                    rowSpacing: 10
                    columnSpacing: 20

                    Column {
                        spacing: 2
                        Text { text: "Device Name"; color: Theme.textSecondary; font.pixelSize: 13 }
                        Text { text: "Raspberry Pi Study Buddy"; font.bold: true; color: Theme.textPrimary; font.pixelSize: 15 }
                    }

                    Column {
                        spacing: 2
                        Text { text: "Device Hardware"; color: Theme.textSecondary; font.pixelSize: 13 }
                        Text { text: "Raspberry Pi Zero 2 W (512 MB)"; font.bold: true; color: Theme.textPrimary; font.pixelSize: 15 }
                    }

                    Column {
                        spacing: 2
                        Text { text: "Display Resolution"; color: Theme.textSecondary; font.pixelSize: 13 }
                        Text { text: "800 × 480 Landscape (5-inch touch)"; font.bold: true; color: Theme.textPrimary; font.pixelSize: 15 }
                    }

                    Column {
                        spacing: 2
                        Text { text: "Application Version"; color: Theme.textSecondary; font.pixelSize: 13 }
                        Text { text: "v" + settingsController.appVersion; font.bold: true; color: Theme.textPrimary; font.pixelSize: 15 }
                    }

                    Column {
                        spacing: 2
                        Text { text: "Device Identity ID"; color: Theme.textSecondary; font.pixelSize: 13 }
                        Text { text: settingsController.deviceId; font.bold: true; color: Theme.textPrimary; font.pixelSize: 14; elide: Text.ElideRight; width: 220 }
                    }

                    Column {
                        spacing: 2
                        Text { text: "Storage Capacity"; color: Theme.textSecondary; font.pixelSize: 13 }
                        Text { text: settingsController.storageUsedGb + " GB / " + settingsController.storageTotalGb + " GB"; font.bold: true; color: Theme.textPrimary; font.pixelSize: 15 }
                    }
                }
            }
        }
    }
}
