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
        title: "Software & System Update"
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
                        width: 28; height: 28
                        source: Assets.update
                        fillMode: Image.PreserveAspectFit
                    }
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: settingsController.updateStatus
                    color: Theme.textPrimary
                    font.pixelSize: Typography.pageTitle
                    font.family: Typography.fontSerif
                    font.bold: true
                }

                Column {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 4
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Current version  ·  v" + settingsController.appVersion
                        color: Theme.textSecondary
                        font.pixelSize: Typography.body
                        font.family: Typography.fontFamily
                    }
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: settingsController.hasUpdate
                              ? "Available version  ·  v" + settingsController.availableVersion
                              : "Raspberry Pi OS  ·  64-bit"
                        color: Theme.textSecondary
                        font.pixelSize: Typography.caption
                        font.family: Typography.fontFamily
                    }
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    visible: settingsController.updateNotes.length > 0
                    text: settingsController.updateNotes
                    color: Theme.textSecondary
                    font.pixelSize: Typography.caption
                    font.family: Typography.fontFamily
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    visible: settingsController.hasUpdate && !settingsController.updateCompatible
                    text: "This release is not compatible with this device or its saved assessment data."
                    color: Theme.error
                    font.pixelSize: Typography.caption
                    font.family: Typography.fontFamily
                }

                ProgressBar {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: Math.min(360, parent.width)
                    visible: settingsController.updateBusy && settingsController.updateProgress > 0
                    progress: settingsController.updateProgress
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    visible: settingsController.updateError.length > 0
                    text: settingsController.updateError
                    color: Theme.error
                    font.pixelSize: Typography.caption
                    font.family: Typography.fontFamily
                }

                Item { width: 1; height: Spacing.xs }

                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: Spacing.md

                    PrimaryButton {
                        text: "Check for Updates"
                        iconSource: Assets.refresh
                        preferredHeight: Metrics.touchNormal
                        enabled: !settingsController.updateBusy
                        onClicked: settingsController.checkUpdate()
                    }

                    PrimaryButton {
                        visible: settingsController.hasUpdate && !settingsController.updatePendingInstall
                        text: settingsController.updateBusy
                              ? (settingsController.updateStatus === "Restarting to install update"
                                 ? "Restarting..."
                                 : settingsController.updateStatus === "Verifying update" ? "Verifying..."
                                 : settingsController.updateProgress > 0 ? "Downloading..." : "Preparing...")
                              : "Download & Install"
                        buttonColor: Theme.forest
                        preferredHeight: Metrics.touchNormal
                        enabled: !settingsController.updateBusy && settingsController.updateCompatible
                        onClicked: settingsController.downloadUpdate()
                    }
                }
            }
        }
    }
}
