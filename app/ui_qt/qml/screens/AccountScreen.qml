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
        title: "Account & Student Profiles"
        profileText: appController.activeProfileName
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

        Row {
            anchors.fill: parent
            spacing: Spacing.md

            // LEFT: Account & Connection Card
            AppCard {
                width: 320
                height: parent.height

                Column {
                    anchors.fill: parent
                    anchors.margins: Spacing.lg
                    spacing: Spacing.sm

                    Text {
                        text: "Cloud Account"
                        color: Theme.textPrimary
                        font.pixelSize: Typography.sectionTitle
                        font.family: Typography.fontSerif
                        font.bold: true
                    }

                    Rectangle {
                        width: parent.width
                        height: 64
                        radius: Metrics.radiusSm
                        color: Theme.surfaceActive
                        border.color: Theme.border
                        border.width: 1

                        Row {
                            anchors.fill: parent
                            anchors.margins: Spacing.sm
                            spacing: Spacing.sm

                            Rectangle {
                                width: 38; height: 38; radius: 19
                                color: Theme.softSage
                                anchors.verticalCenter: parent.verticalCenter
                                Image {
                                    anchors.centerIn: parent
                                    width: 20; height: 20
                                    source: Assets.account
                                    fillMode: Image.PreserveAspectFit
                                }
                            }

                            Column {
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 2
                                Text {
                                    text: settingsController.accountName
                                    font.bold: true
                                    font.pixelSize: Typography.body
                                    font.family: Typography.fontFamily
                                    color: Theme.textPrimary
                                }
                                StatusBadge {
                                    text: settingsController.isPaired ? "Connected to Cloud" : "Not Paired"
                                    statusType: settingsController.isPaired ? "online" : "offline"
                                    implicitHeight: 20
                                }
                            }
                        }
                    }

                    Item { width: 1; height: Spacing.xs }

                    PrimaryButton {
                        width: parent.width
                        preferredHeight: Metrics.touchNormal
                        text: settingsController.isPaired ? "Sync Study Profiles" : "Pair This Raspberry Pi"
                        iconSource: Assets.sync
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
                        preferredHeight: Metrics.touchNormal
                        visible: settingsController.isPaired
                        text: "Unlink Device"
                        textColor: Theme.terracotta
                        borderColor: Theme.terracotta
                        onClicked: settingsController.disconnectAccount()
                    }
                }
            }

            // RIGHT: Active Study Profiles Card
            AppCard {
                width: parent.width - 320 - Spacing.md
                height: parent.height

                Column {
                    anchors.fill: parent
                    anchors.margins: Spacing.lg
                    spacing: Spacing.sm

                    Row {
                        width: parent.width
                        Text {
                            text: "Active Profiles (" + profileController.profileCount + " of 3)"
                            color: Theme.textPrimary
                            font.pixelSize: Typography.sectionTitle
                            font.family: Typography.fontSerif
                            font.bold: true
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
                        height: parent.height - 44
                        clip: true
                        spacing: Spacing.xs
                        visible: profileController.profiles.length > 0
                        model: profileController.profiles

                        delegate: Rectangle {
                            width: parent.width
                            height: 54
                            radius: Metrics.radiusSm
                            color: modelData.isActive ? Theme.surfaceWarm : Theme.surfaceActive
                            border.color: modelData.isActive ? Theme.forest : Theme.border
                            border.width: modelData.isActive ? 2 : 1

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: profileController.selectProfileId(modelData.id)
                            }

                            Item {
                                anchors.fill: parent
                                anchors.margins: Spacing.sm

                                Row {
                                    anchors.left: parent.left
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: Spacing.sm

                                    Rectangle {
                                        width: 32; height: 32; radius: 16
                                        color: modelData.isActive ? Theme.forest : Theme.softSage
                                        anchors.verticalCenter: parent.verticalCenter
                                        Image {
                                            anchors.centerIn: parent
                                            width: 16; height: 16
                                            source: Assets.account
                                            fillMode: Image.PreserveAspectFit
                                        }
                                    }

                                    Column {
                                        anchors.verticalCenter: parent.verticalCenter
                                        spacing: 2
                                        Text {
                                            text: modelData.name
                                            font.bold: true
                                            font.pixelSize: Typography.body
                                            font.family: Typography.fontFamily
                                            color: Theme.textPrimary
                                        }
                                        Text {
                                            text: modelData.grade
                                            font.pixelSize: Typography.caption
                                            font.family: Typography.fontFamily
                                            color: Theme.textSecondary
                                        }
                                    }
                                }

                                StatusBadge {
                                    visible: modelData.isActive
                                    text: "In Use"
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
