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
        title: "Pair a New Device"
        networkText: appController.networkLabel
        syncText: appController.syncLabel
        isOnline: appController.isOnline
        showBack: true
        onBackClicked: appController.navigate("profile_picker")
    }

    AppCard {
        anchors.top: header.bottom
        anchors.topMargin: 8
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 16
        anchors.horizontalCenter: parent.horizontalCenter
        width: 720

        Row {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 24

            // Left side: Pairing code card
            Column {
                width: 320
                spacing: 12

                Text {
                    text: "Pairing Code"
                    color: Theme.textSecondary
                    font.pixelSize: Theme.fontSizeSecondary
                    font.family: Theme.fontFamily
                }

                // Large code block
                Rectangle {
                    width: parent.width
                    height: 90
                    radius: 14
                    color: Theme.surfaceSelected
                    border.color: Theme.primary
                    border.width: 2

                    Text {
                        anchors.centerIn: parent
                        text: settingsController.pairingCode.split("").join(" ")
                        color: Theme.primaryDark
                        font.pixelSize: 34
                        font.bold: true
                        font.letterSpacing: 4
                        font.family: Theme.fontFamily
                    }
                }

                Row {
                    spacing: 6
                    Text {
                        text: "⏱"
                        font.pixelSize: 14
                    }
                    Text {
                        text: "Valid for 10 minutes"
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontSizeCaption
                        font.family: Theme.fontFamily
                    }
                }

                Item { width: 1; height: 6 }

                PrimaryButton {
                    width: parent.width
                    preferredHeight: Theme.touchNormal
                    text: "Generate New Code"
                    iconSource: Assets.refresh
                    onClicked: settingsController.requestPairingCode()
                }
            }

            // Right side: Step by step instructions
            Column {
                width: parent.width - 320 - 24
                spacing: 12

                Text {
                    text: "Connect to your Web Account"
                    color: Theme.textPrimary
                    font.pixelSize: Theme.fontSizeHeading
                    font.bold: true
                    font.family: Theme.fontFamily
                }

                Column {
                    spacing: 10
                    width: parent.width

                    Row {
                        spacing: 10
                        Rectangle {
                            width: 24; height: 24; radius: 12
                            color: Theme.primaryLight
                            Text { anchors.centerIn: parent; text: "1"; font.bold: true; color: Theme.primaryDark }
                        }
                        Text {
                            text: "Log in on the website on your computer or phone"
                            color: Theme.textPrimary
                            font.pixelSize: Theme.fontSizeSecondary
                            wrapMode: Text.Wrap
                            width: parent.width - 34
                        }
                    }

                    Row {
                        spacing: 10
                        Rectangle {
                            width: 24; height: 24; radius: 12
                            color: Theme.primaryLight
                            Text { anchors.centerIn: parent; text: "2"; font.bold: true; color: Theme.primaryDark }
                        }
                        Text {
                            text: "Go to Account & Devices → Connect Raspberry Pi"
                            color: Theme.textPrimary
                            font.pixelSize: Theme.fontSizeSecondary
                            wrapMode: Text.Wrap
                            width: parent.width - 34
                        }
                    }

                    Row {
                        spacing: 10
                        Rectangle {
                            width: 24; height: 24; radius: 12
                            color: Theme.primaryLight
                            Text { anchors.centerIn: parent; text: "3"; font.bold: true; color: Theme.primaryDark }
                        }
                        Text {
                            text: "Enter this 6-character code to link your learning"
                            color: Theme.textPrimary
                            font.pixelSize: Theme.fontSizeSecondary
                            wrapMode: Text.Wrap
                            width: parent.width - 34
                        }
                    }
                }

                Item { width: 1; height: 6 }

                SecondaryButton {
                    width: parent.width
                    preferredHeight: Theme.touchNormal
                    text: "Skip (Use Offline Profiles)"
                    onClicked: appController.navigate("profile_picker")
                }
            }
        }
    }
}
