import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.background
    readonly property var updateWork: settingsController.updateWork
    Component.onCompleted: settingsController.refreshUpdateState()

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
            width: Math.min(520, parent.width)
            implicitHeight: contentCol.implicitHeight + Spacing.xl * 2

            Column {
                id: contentCol
                anchors.centerIn: parent
                width: parent.width - Spacing.xl * 2
                spacing: Spacing.md

                Rectangle {
                    width: 56; height: 56; radius: 28
                    color: Theme.primaryLight
                    anchors.horizontalCenter: parent.horizontalCenter
                    Image {
                        anchors.centerIn: parent
                        width: 28; height: 28
                        source: Assets.update
                        fillMode: Image.PreserveAspectFit
                    }
                }

                Text {
                    objectName: "softwareUpdateStatus"
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
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
                        objectName: "softwareCurrentVersion"
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Current version · v" + settingsController.appVersion
                        color: Theme.textSecondary
                        font.pixelSize: Typography.body
                        font.family: Typography.fontFamily
                    }
                    Text {
                        objectName: "softwareAvailableVersion"
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: {
                            const active = settingsController.activeReleaseVersion
                            if (active && active !== settingsController.appVersion)
                                return "Active release · v" + active
                            return settingsController.hasUpdate
                                ? "Available version · v" + settingsController.availableVersion
                                : settingsController.updateReminderVersion
                                  ? "Last found · v" + settingsController.updateReminderVersion
                                  : "Raspberry Pi OS · 64-bit"
                        }
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
                    visible: settingsController.updateNotes.length > 0 && !settingsController.updateBusy
                    text: settingsController.updateNotes
                    color: Theme.textSecondary
                    font.pixelSize: Typography.caption
                    font.family: Typography.fontFamily
                }

                Text {
                    objectName: "softwareCompatibilityWarning"
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

                Column {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: Math.min(360, parent.width)
                    spacing: Spacing.xs
                    visible: !!root.updateWork.label

                    ProgressBar {
                        objectName: "softwareUpdateProgress"
                        width: parent.width
                        progress: root.updateWork.fraction || 0
                        indeterminate: !!root.updateWork.indeterminate
                        Accessible.role: Accessible.ProgressBar
                        Accessible.name: settingsController.updateStatus
                        Accessible.description: progressLabel.text
                    }

                    Text {
                        id: progressLabel
                        objectName: "softwareUpdateProgressLabel"
                        width: parent.width
                        horizontalAlignment: Text.AlignHCenter
                        text: root.updateWork.label || ""
                        wrapMode: Text.WordWrap
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
                    visible: settingsController.updateError.length > 0
                    text: settingsController.updateError
                    color: Theme.error
                    font.pixelSize: Typography.caption
                    font.family: Typography.fontFamily
                }

                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: Spacing.md
                    visible: !settingsController.updateBusy

                    PrimaryButton {
                        text: "Check for Updates"
                        iconSource: Assets.refresh
                        preferredHeight: Metrics.touchNormal
                        onClicked: settingsController.checkUpdate()
                    }

                    PrimaryButton {
                        objectName: "softwareInstallButton"
                        visible: settingsController.hasUpdate && !settingsController.updatePendingInstall
                        text: "Download & Install"
                        buttonColor: Theme.forest
                        preferredHeight: Metrics.touchNormal
                        enabled: settingsController.updateCompatible
                        onClicked: settingsController.downloadUpdate()
                    }
                }
            }
        }
    }
}
