import QtQuick 2.15
import QtQuick.Controls 2.15 as Controls
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.background

    Controls.Dialog {
        id: unlinkDialog
        objectName: "unlinkConfirmation"
        property string profileId: ""
        property string profileName: ""
        anchors.centerIn: parent
        width: 420
        modal: true
        title: profileId ? "Unlink Study Profile?" : "Unlink Account?"
        standardButtons: Controls.Dialog.Ok | Controls.Dialog.Cancel
        contentItem: Text {
            text: unlinkDialog.profileId
                  ? "Remove " + unlinkDialog.profileName + " from this Pi? Other profiles will stay linked. Saved work stays on the device."
                  : "Disconnect this account and its Study Profiles from this Pi? Saved work stays on the device."
            wrapMode: Text.WordWrap
        }
        onAccepted: {
            if (profileId)
                settingsController.unlinkProfile(profileId)
            else
                settingsController.disconnectAccount()
        }
    }

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
                                width: parent.width - 38 - Spacing.sm
                                spacing: 2
                                Text {
                                    width: parent.width
                                    text: settingsController.accountName
                                    elide: Text.ElideRight
                                    font.bold: true
                                    font.pixelSize: Typography.body
                                    font.family: Typography.fontFamily
                                    color: Theme.textPrimary
                                }
                                StatusBadge {
                                    text: settingsController.accountStatus
                                    statusType: settingsController.accountStatus === "Connected" ? "online" : "offline"
                                    implicitHeight: 20
                                }
                            }
                        }
                    }

                    Item { width: 1; height: Spacing.xs }

                    PrimaryButton {
                        objectName: "accountSyncButton"
                        width: parent.width
                        preferredHeight: Metrics.touchNormal
                        text: settingsController.unlinkPending ? "Retry Unlink"
                              : settingsController.isSyncing ? "Syncing…"
                              : settingsController.hasAccount && settingsController.isPaired ? "Sync Now" : "Link Account"
                        enabled: !settingsController.accountActionBusy && !settingsController.isSyncing
                        iconSource: Assets.sync
                        onClicked: {
                            if (settingsController.unlinkPending) {
                                settingsController.retryUnlink();
                            } else if (settingsController.hasAccount && settingsController.isPaired) {
                                settingsController.startSync();
                            } else {
                                appController.navigate("pairing");
                            }
                        }
                    }

                    SecondaryButton {
                        width: parent.width
                        preferredHeight: Metrics.touchNormal
                        objectName: "unlinkAccountButton"
                        visible: settingsController.hasAccount
                        enabled: !settingsController.accountActionBusy && !settingsController.unlinkPending
                        text: "Unlink Account"
                        textColor: Theme.terracotta
                        borderColor: Theme.terracotta
                        onClicked: {
                            unlinkDialog.profileId = ""
                            unlinkDialog.open()
                        }
                    }

                    Text {
                        objectName: "unlinkStatus"
                        width: parent.width
                        visible: text.length > 0
                        text: settingsController.unlinkStatus
                        color: Theme.textSecondary
                        font.pixelSize: Typography.caption
                        wrapMode: Text.WordWrap
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
                            text: "Study Profiles (" + profileController.profileCount + ")"
                            color: Theme.textPrimary
                            font.pixelSize: Typography.sectionTitle
                            font.family: Typography.fontSerif
                            font.bold: true
                        }
                    }

                    SecondaryButton {
                        width: parent.width
                        visible: profileController.profileCount > 0
                        enabled: !settingsController.accountActionBusy
                        text: "Switch Profile"
                        onClicked: profileController.switchProfile()
                    }

                    EmptyState {
                        visible: profileController.profiles.length === 0
                        title: "No Study Profiles Found"
                        description: "There are no linked Study Profiles available on this Pi."
                        actionText: profileController.canAddProfile && settingsController.hasAccount
                                    && !settingsController.accountActionBusy && !settingsController.unlinkPending
                                    ? "Create Profile" : ""
                        onActionClicked: appController.navigate("create_profile")
                    }

                    ListView {
                        width: parent.width
                        height: parent.height - 96
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

                            Item {
                                anchors.fill: parent
                                anchors.margins: Spacing.sm

                                Row {
                                    width: parent.width - 140
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
                                        width: parent.width - 32 - Spacing.sm
                                        anchors.verticalCenter: parent.verticalCenter
                                        spacing: 2
                                        Text {
                                            width: parent.width
                                            text: modelData.name
                                            elide: Text.ElideRight
                                            font.bold: true
                                            font.pixelSize: Typography.body
                                            font.family: Typography.fontFamily
                                            color: Theme.textPrimary
                                        }
                                        Text {
                                            width: parent.width
                                            text: modelData.grade || (modelData.isActive ? "In use" : "")
                                            elide: Text.ElideRight
                                            font.pixelSize: Typography.caption
                                            font.family: Typography.fontFamily
                                            color: Theme.textSecondary
                                        }
                                    }
                                }

                                SecondaryButton {
                                    objectName: "unlinkProfileButton"
                                    visible: settingsController.hasAccount && modelData.isLinked
                                    enabled: !settingsController.accountActionBusy && !settingsController.unlinkPending
                                    text: "Unlink Profile"
                                    textColor: Theme.terracotta
                                    preferredHeight: Metrics.touchMin
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    onClicked: {
                                        unlinkDialog.profileId = modelData.id
                                        unlinkDialog.profileName = modelData.name
                                        unlinkDialog.open()
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
