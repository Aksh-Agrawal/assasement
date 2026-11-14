import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    anchors.fill: parent
    color: Theme.background

    Component.onCompleted: {
        if ((!settingsController.hasAccount || !settingsController.isPaired)
                && !settingsController.pairingCode && !settingsController.pairingError) {
            settingsController.requestPairingCode();
        }
    }

    AppHeader {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        title: "Connect Your Questraa Account"
        networkText: appController.networkLabel
        syncText: appController.syncLabel
        isOnline: appController.isOnline
        showBack: appController.canGoBack
        onBackClicked: appController.goBack()
    }

    Row {
        anchors.top: header.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: Spacing.lg
        spacing: Spacing.md

        AppCard {
            id: codeCard
            width: Math.round((parent.width - Spacing.md) * 0.44)
            height: parent.height

            Column {
                anchors.fill: parent
                anchors.margins: Spacing.lg
                spacing: Spacing.lg

                Text {
                    text: "Pairing code"
                    color: Theme.textPrimary
                    font.pixelSize: Typography.sectionTitle
                    font.family: Typography.fontSerif
                    font.bold: true
                }

                Rectangle {
                    width: parent.width
                    height: 84
                    radius: Metrics.radiusMd
                    color: Theme.surfaceActive
                    border.color: Theme.border

                    Text {
                        anchors.centerIn: parent
                        text: settingsController.pairingCode
                            ? settingsController.pairingCode.split("").join(" ") : "– – – – – –"
                        color: Theme.forest
                        font.pixelSize: Typography.hero
                        font.family: Typography.fontSerif
                        font.bold: true
                    }
                }

                Text {
                    objectName: "pairingStatusText"
                    width: parent.width
                    text: settingsController.pairingStatus
                    wrapMode: Text.WordWrap
                    color: settingsController.pairingError ? Theme.error : Theme.textSecondary
                    font.pixelSize: Typography.body
                    font.family: Typography.family
                }

                PrimaryButton {
                    objectName: "pairingRetryButton"
                    width: parent.width
                    text: settingsController.canRetryAccountSync ? "Retry Profile Sync"
                          : settingsController.pairingCode ? "Generate New Code" : "Generate Pairing Code"
                    enabled: !settingsController.accountActionBusy && !settingsController.unlinkPending
                    onClicked: settingsController.requestPairingCode()
                }

                SecondaryButton {
                    width: parent.width
                    text: "Wi-Fi Settings"
                    onClicked: appController.navigate("wifi")
                }
            }
        }

        AppCard {
            width: parent.width - codeCard.width - Spacing.md
            height: parent.height

            Column {
                anchors.fill: parent
                anchors.margins: Spacing.lg
                spacing: Spacing.lg

                Text {
                    width: parent.width
                    text: "Use your existing account"
                    color: Theme.textPrimary
                    font.pixelSize: Typography.pageTitle
                    font.family: Typography.fontSerif
                    font.bold: true
                    wrapMode: Text.WordWrap
                }

                Repeater {
                    model: [
                        "1. Sign in to the Questraa learning portal on your phone or computer.",
                        "2. Open Account & Devices and select Connect Raspberry Pi.",
                        "3. Enter the pairing code shown here and confirm."
                    ]

                    Text {
                        width: parent.width
                        text: modelData
                        color: Theme.textSecondary
                        font.pixelSize: Typography.body
                        font.family: Typography.family
                        wrapMode: Text.WordWrap
                    }
                }

                Text {
                    width: parent.width
                    text: "Your existing Study Profiles will appear here after you connect."
                    color: Theme.textPrimary
                    font.pixelSize: Typography.body
                    font.family: Typography.family
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
}
