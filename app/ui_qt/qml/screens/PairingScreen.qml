import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.background

    Component.onCompleted: {
        if (typeof settingsController !== "undefined" && settingsController) {
            if (!settingsController.isPaired && (!settingsController.pairingCode || settingsController.pairingCode === "")) {
                settingsController.requestPairingCode();
            }
        }
    }

    AppHeader {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        title: "Link Device to Web Account"
        networkText: appController.networkLabel
        syncText: appController.syncLabel
        isOnline: appController.isOnline
        showBack: true
        onBackClicked: appController.navigate("profile_picker")
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

            // Left side: Pairing code ticket
            AppCard {
                width: 330
                height: parent.height

                Column {
                    anchors.fill: parent
                    anchors.margins: Spacing.lg
                    spacing: Spacing.sm

                    Row {
                        spacing: Spacing.sm
                        Rectangle {
                            width: 36
                            height: 36
                            radius: Metrics.radiusSm
                            color: Theme.surfaceActive
                            border.color: Theme.border
                            border.width: 1
                            Image {
                                anchors.centerIn: parent
                                width: 22
                                height: 22
                                source: Assets.device_pairing
                                fillMode: Image.PreserveAspectFit
                            }
                        }
                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            Text {
                                text: "Pairing Ticket"
                                color: Theme.textPrimary
                                font.pixelSize: Typography.sectionTitle
                                font.family: Typography.fontSerif
                                font.bold: true
                            }
                            Text {
                                text: "One-time device connection"
                                color: Theme.textSecondary
                                font.pixelSize: Typography.caption
                                font.family: Typography.fontFamily
                            }
                        }
                    }

                    // Ticket code container
                    Rectangle {
                        width: parent.width
                        height: 84
                        radius: Metrics.radiusMd
                        color: Theme.surfaceWarm
                        border.color: Theme.border
                        border.width: 1

                        Column {
                            anchors.centerIn: parent
                            spacing: 4

                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: {
                                    if (typeof settingsController !== "undefined" && settingsController) {
                                        if (settingsController.pairingStatus === "generating" || settingsController.pairingStatus === "Generating…") {
                                            return "G E N . . ."
                                        }
                                        if (settingsController.pairingCode && settingsController.pairingCode.length > 0) {
                                            return (settingsController.pairingCode + "").split("").join(" ")
                                        }
                                    }
                                    return "- - - - - -"
                                }
                                color: Theme.forest
                                font.pixelSize: 32
                                font.bold: true
                                font.letterSpacing: 4
                                font.family: Typography.fontSerif
                            }

                            Row {
                                anchors.horizontalCenter: parent.horizontalCenter
                                spacing: 4
                                Text {
                                    text: "Valid for 10 minutes • Generated on Pi"
                                    color: Theme.textSecondary
                                    font.pixelSize: Typography.caption
                                    font.family: Typography.fontFamily
                                }
                            }
                        }
                    }

                    Text {
                        text: "Enter this code on your phone or computer to link this Pi to your learning cloud."
                        color: Theme.textSecondary
                        font.pixelSize: Typography.metadata
                        font.family: Typography.fontFamily
                        wrapMode: Text.Wrap
                        width: parent.width
                        lineHeight: 1.25
                    }

                    Item { width: 1; height: Spacing.xs }

                    PrimaryButton {
                        width: parent.width
                        preferredHeight: Metrics.touchNormal
                        text: "Generate New Code"
                        iconSource: Assets.refresh
                        onClicked: settingsController.requestPairingCode()
                    }
                }
            }

            // Right side: Editorial instructions & testing mode
            AppCard {
                width: parent.width - 330 - Spacing.md
                height: parent.height

                Column {
                    anchors.fill: parent
                    anchors.margins: Spacing.md
                    spacing: Spacing.sm

                    // Testing / Offline Mode Callout
                    Rectangle {
                        width: parent.width
                        height: 130
                        radius: Metrics.radiusMedium
                        color: Theme.surfaceWarm
                        border.color: Theme.border
                        border.width: 1

                        Column {
                            anchors.fill: parent
                            anchors.margins: Spacing.sm
                            spacing: Spacing.xs

                            Text {
                                text: "Testing & Offline Mode"
                                color: Theme.deepInk
                                font.pixelSize: Typography.sectionTitle
                                font.family: Typography.fontSerif
                                font.bold: true
                            }

                            Text {
                                text: "Practice immediately on this laptop without cloud pairing."
                                color: Theme.textSecondary
                                font.pixelSize: Typography.caption
                                font.family: Typography.fontFamily
                            }

                            Item { width: 1; height: 2 }

                            Row {
                                width: parent.width
                                spacing: Spacing.sm

                                PrimaryButton {
                                    width: (parent.width - Spacing.sm) * 0.6
                                    preferredHeight: 38
                                    text: "Start Testing Mode →"
                                    buttonColor: Theme.forest
                                    onClicked: profileController.startTestingMode()
                                }

                                SecondaryButton {
                                    width: (parent.width - Spacing.sm) * 0.4
                                    preferredHeight: 38
                                    text: "Profiles..."
                                    onClicked: appController.navigate("profile_picker")
                                }
                            }
                        }
                    }

                    // Cloud Linking Steps
                    Text {
                        text: "Or Link to Cloud Account"
                        color: Theme.textPrimary
                        font.pixelSize: Typography.body
                        font.family: Typography.fontSerif
                        font.bold: true
                    }

                    Column {
                        id: instructionsCol
                        width: parent.width
                        spacing: 6

                        Row {
                            spacing: Spacing.sm
                            Rectangle {
                                width: 22; height: 22; radius: 11
                                color: Theme.softSage
                                Text { anchors.centerIn: parent; text: "1"; font.bold: true; color: Theme.deepInk; font.pixelSize: 11 }
                            }
                            Text {
                                text: "Log in on learning portal on your phone or PC"
                                color: Theme.textSecondary
                                font.pixelSize: Typography.caption
                                font.family: Typography.fontFamily
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }

                        Row {
                            spacing: Spacing.sm
                            Rectangle {
                                width: 22; height: 22; radius: 11
                                color: Theme.softSage
                                Text { anchors.centerIn: parent; text: "2"; font.bold: true; color: Theme.deepInk; font.pixelSize: 11 }
                            }
                            Text {
                                text: "Go to Account & Devices → Connect Device"
                                color: Theme.textSecondary
                                font.pixelSize: Typography.caption
                                font.family: Typography.fontFamily
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }

                        Row {
                            spacing: Spacing.sm
                            Rectangle {
                                width: 22; height: 22; radius: 11
                                color: Theme.softSage
                                Text { anchors.centerIn: parent; text: "3"; font.bold: true; color: Theme.deepInk; font.pixelSize: 11 }
                            }
                            Text {
                                text: "Enter 6-digit code shown on the left"
                                color: Theme.textSecondary
                                font.pixelSize: Typography.caption
                                font.family: Typography.fontFamily
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }
                    }
                }
            }
        }
    }
}
