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
        title: "Account & Profiles"
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

        Row {
            anchors.fill: parent
            spacing: 16

            // LEFT: Account & Connection Card
            AppCard {
                width: 320
                height: parent.height

                Column {
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 12

                    Text {
                        text: "Connected Account"
                        color: Theme.textPrimary
                        font.pixelSize: Theme.fontSizeHeading
                        font.bold: true
                        font.family: Theme.fontFamily
                    }

                    Rectangle {
                        width: parent.width
                        height: 64
                        radius: 12
                        color: Theme.surfaceActive

                        Row {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 10

                            Rectangle {
                                width: 40; height: 40; radius: 20
                                color: Theme.primaryLight
                                Image { anchors.centerIn: parent; width: 22; height: 22; source: "../icons/account.svg" }
                            }

                            Column {
                                anchors.verticalCenter: parent.verticalCenter
                                Text { text: settingsController.accountName; font.bold: true; font.pixelSize: 15; color: Theme.textPrimary }
                                StatusBadge {
                                    text: settingsController.isPaired ? "Connected" : "Unpaired"
                                    statusType: settingsController.isPaired ? "online" : "offline"
                                    implicitHeight: 22
                                }
                            }
                        }
                    }

                    Item { width: 1; height: 8 }

                    PrimaryButton {
                        width: parent.width
                        preferredHeight: Theme.touchNormal
                        text: settingsController.isPaired ? "Sync Study Profiles" : "Pair This Raspberry Pi"
                        iconSource: "../icons/sync.svg"
                        onClicked: {
                            if (settingsController.isPaired) {
                                settingsController.syncProfiles();
                            } else {
                                appController.navigate("pairing");
                            }
                        }
                    }

                    SecondaryButton {
                        width: parent.width
                        preferredHeight: Theme.touchNormal
                        visible: settingsController.isPaired
                        text: "Unlink Device"
                        textColor: Theme.warning
                        borderColor: Theme.warning
                        onClicked: settingsController.disconnectAccount()
                    }
                }
            }

            // RIGHT: Active Study Profiles Card
            AppCard {
                width: parent.width - 320 - 16
                height: parent.height

                Column {
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 10

                    Row {
                        width: parent.width
                        Text {
                            text: "Study Profiles (" + profileController.profileCount + " of 3)"
                            color: Theme.textPrimary
                            font.pixelSize: Theme.fontSizeHeading
                            font.bold: true
                            font.family: Theme.fontFamily
                        }
                    }

                    EmptyState {
                        anchors.centerIn: parent
                        visible: profileController.profiles.length === 0
                        title: "No Study Profiles Found"
                        description: "Add a local profile or sync your cloud account to link profiles."
                        actionText: "Create Profile"
                        onActionClicked: appController.navigate("create_profile")
                    }

                    ListView {
                        width: parent.width
                        height: parent.height - 40
                        clip: true
                        spacing: 8
                        visible: profileController.profiles.length > 0
                        model: profileController.profiles

                        delegate: Rectangle {
                            width: parent.width
                            height: 56
                            radius: 10
                            color: Theme.surfaceActive
                            border.color: modelData.isActive ? Theme.primary : Theme.border
                            border.width: modelData.isActive ? 2 : 1

                            Item {
                                anchors.fill: parent
                                anchors.margins: 12

                                Row {
                                    anchors.left: parent.left
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 10

                                    Rectangle {
                                        width: 32; height: 32; radius: 16
                                        color: modelData.isActive ? Theme.primaryLight : Theme.surface
                                        Image { anchors.centerIn: parent; width: 18; height: 18; source: "../icons/account.svg" }
                                    }

                                    Column {
                                        anchors.verticalCenter: parent.verticalCenter
                                        Text { text: modelData.name; font.bold: true; font.pixelSize: 15; color: Theme.textPrimary }
                                        Text { text: modelData.grade; font.pixelSize: 12; color: Theme.textSecondary }
                                    }
                                }

                                StatusBadge {
                                    visible: modelData.isActive
                                    text: "Active Profile"
                                    statusType: "success"
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
