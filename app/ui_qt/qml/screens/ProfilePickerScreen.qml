import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.canvas
    readonly property bool showProfiles: settingsController.hasAccount || profileController.canStartTesting

    AppHeader {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        title: !root.showProfiles ? "Connect Your Account"
               : profileController.switchMode ? "Switch Study Profile" : "Who's studying today?"
        showBack: profileController.switchMode
        onBackClicked: profileController.cancelSwitch()
        networkText: appController.networkLabel
        syncText: appController.syncLabel
        isOnline: appController.isOnline
    }

    Item {
        anchors.top: header.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: Spacing.lg

        // Horizontal Row of Learner Cards
        Row {
            visible: root.showProfiles
            anchors.centerIn: parent
            anchors.verticalCenterOffset: profileController.switchMode ? 0 : -16
            spacing: Spacing.xl

            Repeater {
                model: root.showProfiles ? profileController.profiles : []

                delegate: AppCard {
                    width: 175
                    height: 230
                    interactive: true
                    selected: modelData.isActive
                    onClicked: profileController.selectProfileId(modelData.id)

                    Column {
                        anchors.centerIn: parent
                        spacing: Spacing.md
                        width: parent.width - 24

                        // Learner Avatar medallion
                        Rectangle {
                            width: 68
                            height: 68
                            radius: 34
                            color: modelData.isActive ? Theme.primaryLight : Theme.surfaceActive
                            border.color: modelData.isActive ? Theme.forest : Theme.border
                            border.width: modelData.isActive ? 2 : 1
                            anchors.horizontalCenter: parent.horizontalCenter

                            Image {
                                anchors.centerIn: parent
                                width: 36
                                height: 36
                                source: Assets.account
                                fillMode: Image.PreserveAspectFit
                            }

                            // Small lock badge if PIN protected
                            Rectangle {
                                width: 22
                                height: 22
                                radius: 11
                                color: Theme.gold
                                border.color: Theme.deepInk
                                border.width: 1
                                anchors.bottom: parent.bottom
                                anchors.right: parent.right
                                visible: modelData.hasPin

                                Image {
                                    anchors.centerIn: parent
                                    width: 12
                                    height: 12
                                    source: Assets.lock
                                    fillMode: Image.PreserveAspectFit
                                }
                            }
                        }

                        // Student Name
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: modelData.name
                            color: Theme.deepInk
                            font.pixelSize: Typography.sectionTitle
                            font.bold: true
                            font.family: Typography.family
                            elide: Text.ElideRight
                            width: parent.width
                            horizontalAlignment: Text.AlignHCenter
                        }

                        // Exam Context Badge
                        Rectangle {
                            visible: modelData.grade.length > 0
                            anchors.horizontalCenter: parent.horizontalCenter
                            height: 22
                            width: gradeText.implicitWidth + 14
                            radius: 11
                            color: Theme.surfaceActive
                            border.color: Theme.border
                            border.width: 1

                            Text {
                                id: gradeText
                                anchors.centerIn: parent
                                text: modelData.grade
                                color: Theme.mutedInk
                                font.pixelSize: Typography.caption
                                font.bold: true
                                font.family: Typography.family
                            }
                        }

                        // Status marker
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: modelData.isActive ? "Current Profile" : "Tap to select"
                            color: modelData.isActive ? Theme.forest : Theme.mutedInk
                            font.pixelSize: Typography.caption
                            font.bold: modelData.isActive
                            font.family: Typography.family
                        }
                    }
                }
            }

            // Add Profile Card
            Rectangle {
                objectName: "createStudyProfileCard"
                visible: profileController.canAddProfile && !profileController.switchMode
                width: 155
                height: 230
                radius: Metrics.radiusLarge
                color: addMouse.containsPress ? Theme.surfaceActive : "transparent"
                border.color: Theme.border
                border.width: 1.5

                Column {
                    anchors.centerIn: parent
                    spacing: Spacing.md
                    width: parent.width - 24

                    Rectangle {
                        width: 52
                        height: 52
                        radius: 26
                        color: Theme.surfaceActive
                        border.color: Theme.border
                        border.width: 1
                        anchors.horizontalCenter: parent.horizontalCenter

                        Image {
                            anchors.centerIn: parent
                            width: 24
                            height: 24
                            source: Assets.plus
                            fillMode: Image.PreserveAspectFit
                        }
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Add Study Profile"
                        color: Theme.deepInk
                        font.pixelSize: Typography.body
                        font.bold: true
                        font.family: Typography.family
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Create profile"
                        color: Theme.mutedInk
                        font.pixelSize: Typography.caption
                        font.family: Typography.family
                    }
                }

                MouseArea {
                    id: addMouse
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: appController.navigate("create_profile")
                }
            }
        }

        Column {
            anchors.centerIn: parent
            spacing: Spacing.lg
            visible: !root.showProfiles

            Text {
                text: "Connect your Questraa account to see your Study Profiles."
                color: Theme.textPrimary
                font.family: Typography.family
                font.pixelSize: Typography.body
            }

            PrimaryButton {
                objectName: "connectExistingAccountButton"
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Connect Existing Account"
                onClicked: appController.navigate("pairing")
            }
        }

        SecondaryButton {
            objectName: "reconnectAccountButton"
            anchors.bottom: parent.bottom
            anchors.horizontalCenter: parent.horizontalCenter
            visible: settingsController.hasAccount && !settingsController.isPaired && !profileController.switchMode
            text: "Reconnect Account"
            onClicked: appController.navigate("pairing")
        }

        // Quick Start banner for testing mode
        Row {
            anchors.bottom: parent.bottom
            anchors.bottomMargin: Spacing.xs
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: Spacing.md
            visible: !profileController.switchMode && profileController.canStartTesting

            SecondaryButton {
                preferredHeight: 36
                text: "Quick Start (Testing Mode)"
                onClicked: profileController.startTestingMode()
            }
        }
    }

    // Modal: PIN Entry
    PinModal {
        id: pinModal
        visible: profileController.pinLocked
        profileName: profileController.pinProfileName
        errorMessage: profileController.pinError
        onPinSubmitted: function(pin) {
            profileController.submitPin(pin);
        }
        onCancelled: {
            profileController.cancelPin();
        }
    }
}
