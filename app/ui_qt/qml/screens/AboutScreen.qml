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
        title: "About Study Buddy"
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
            width: 520
            implicitHeight: contentCol.implicitHeight + 40

            Column {
                id: contentCol
                anchors.centerIn: parent
                width: parent.width - 48
                spacing: 14

                Rectangle {
                    width: 60; height: 60; radius: 30
                    color: Theme.surfaceActive
                    border.color: Theme.border
                    anchors.horizontalCenter: parent.horizontalCenter
                    Image { anchors.centerIn: parent; width: 36; height: 36; source: "../icons/raspberry.svg" }
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "Raspberry Pi Study Buddy"
                    color: Theme.textPrimary
                    font.pixelSize: Theme.fontSizeTitle
                    font.bold: true
                    font.family: Theme.fontFamily
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "A calm, focused, offline-first learning companion."
                    color: Theme.textSecondary
                    font.pixelSize: Theme.fontSizeSecondary
                    font.family: Theme.fontFamily
                }

                Rectangle { width: parent.width; height: 1; color: Theme.divider }

                Column {
                    width: parent.width
                    spacing: 6
                    Text { text: "App Version: v" + settingsController.appVersion; font.pixelSize: 14; color: Theme.textPrimary }
                    Text { text: "Device Hardware: Raspberry Pi Zero 2 W (512 MB)"; font.pixelSize: 14; color: Theme.textPrimary }
                    Text { text: "GUI Framework: Qt Quick 2 / PySide6 (Embedded Appliance)"; font.pixelSize: 14; color: Theme.textPrimary }
                    Text { text: "License: Open source educational software. PySide6 LGPL v3."; font.pixelSize: 13; color: Theme.textSecondary }
                }

                Item { width: 1; height: 4 }

                PrimaryButton {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "Back to Settings"
                    preferredHeight: Theme.touchNormal
                    onClicked: appController.navigate("settings")
                }
            }
        }
    }
}
