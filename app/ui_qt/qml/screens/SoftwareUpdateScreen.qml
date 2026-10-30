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
        title: "Software Update"
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
            width: 540
            implicitHeight: contentCol.implicitHeight + 44

            Column {
                id: contentCol
                anchors.centerIn: parent
                width: parent.width - 48
                spacing: 16

                Rectangle {
                    width: 56; height: 56; radius: 28
                    color: Theme.primaryLight
                    anchors.horizontalCenter: parent.horizontalCenter
                    Image { anchors.centerIn: parent; width: 28; height: 28; source: "../icons/update.svg" }
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: settingsController.updateStatus
                    color: Theme.textPrimary
                    font.pixelSize: Theme.fontSizeHeading
                    font.bold: true
                    font.family: Theme.fontFamily
                }

                Column {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 4
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Installed Application Version: v" + settingsController.appVersion
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontSizeSecondary
                    }
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Operating System: Raspberry Pi OS (Bookworm 64-bit)"
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontSizeCaption
                    }
                }

                Item { width: 1; height: 6 }

                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 14

                    PrimaryButton {
                        text: "Check for Updates"
                        iconSource: "../icons/refresh.svg"
                        onClicked: settingsController.checkUpdate()
                    }

                    PrimaryButton {
                        visible: settingsController.hasUpdate
                        text: "Download Update"
                        buttonColor: Theme.primaryDark
                        onClicked: settingsController.downloadUpdate()
                    }
                }
            }
        }
    }
}
