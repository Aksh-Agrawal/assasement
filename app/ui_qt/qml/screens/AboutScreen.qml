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
        anchors.margins: Spacing.md

        AppCard {
            anchors.centerIn: parent
            width: 520
            implicitHeight: contentCol.implicitHeight + Spacing.xl * 2

            Column {
                id: contentCol
                anchors.centerIn: parent
                width: parent.width - Spacing.xl * 2
                spacing: Spacing.md

                Rectangle {
                    width: 56; height: 56; radius: 28
                    color: Theme.softSage
                    anchors.horizontalCenter: parent.horizontalCenter
                    Image {
                        anchors.centerIn: parent
                        width: 32; height: 32
                        source: Assets.raspberry
                        fillMode: Image.PreserveAspectFit
                    }
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "Raspberry Pi Study Buddy"
                    color: Theme.textPrimary
                    font.pixelSize: Typography.pageTitle
                    font.family: Typography.fontSerif
                    font.bold: true
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "A calm, focused, offline-first educational device designed for uninterrupted learning."
                    color: Theme.textSecondary
                    font.pixelSize: Typography.body
                    font.family: Typography.fontFamily
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.Wrap
                    width: parent.width
                }

                Rectangle { width: parent.width; height: 1; color: Theme.divider }

                Column {
                    width: parent.width
                    spacing: Spacing.xs
                    Text { text: "App Version: v" + settingsController.appVersion; font.pixelSize: Typography.metadata; font.family: Typography.fontFamily; color: Theme.textPrimary }
                    Text { text: "Hardware Platform: Raspberry Pi Zero 2 W (512 MB)"; font.pixelSize: Typography.metadata; font.family: Typography.fontFamily; color: Theme.textPrimary }
                    Text { text: "User Interface: PySide6 & Qt Quick 2 (Tactile Educational Design)"; font.pixelSize: Typography.metadata; font.family: Typography.fontFamily; color: Theme.textPrimary }
                    Text { text: "License: Open source educational software. PySide6 LGPL v3."; font.pixelSize: Typography.caption; font.family: Typography.fontFamily; color: Theme.textSecondary }
                }

                Item { width: 1; height: Spacing.xs }

                PrimaryButton {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "Back to Settings"
                    preferredHeight: Metrics.touchNormal
                    onClicked: appController.navigate("settings")
                }
            }
        }
    }
}
