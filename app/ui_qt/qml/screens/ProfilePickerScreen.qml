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
        title: "Who's studying today?"
        networkText: appController.networkLabel
        syncText: appController.syncLabel
        isOnline: appController.isOnline
    }

    Item {
        anchors.top: header.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 16

        // Horizontal Row of Profile Cards (Max 3 profiles + Create Profile)
        Row {
            anchors.centerIn: parent
            spacing: 16

            Repeater {
                model: profileController.profiles

                delegate: AppCard {
                    width: 170
                    height: 240
                    interactive: true
                    selected: modelData.isActive
                    onClicked: profileController.selectProfile(modelData.index)

                    Column {
                        anchors.centerIn: parent
                        spacing: 10
                        width: parent.width - 24

                        // Avatar circle
                        Rectangle {
                            width: 64
                            height: 64
                            radius: 32
                            color: modelData.isActive ? Theme.primaryLight : Theme.surfaceActive
                            border.color: modelData.isActive ? Theme.primary : Theme.border
                            border.width: 1
                            anchors.horizontalCenter: parent.horizontalCenter

                            Image {
                                anchors.centerIn: parent
                                width: 34
                                height: 34
                                source: "../icons/account.svg"
                                fillMode: Image.PreserveAspectFit
                            }

                            // Small lock badge if PIN protected
                            Rectangle {
                                width: 20
                                height: 20
                                radius: 10
                                color: Theme.highlight
                                anchors.bottom: parent.bottom
                                anchors.right: parent.right
                                visible: modelData.hasPin

                                Image {
                                    anchors.centerIn: parent
                                    width: 12
                                    height: 12
                                    source: "../icons/lock.svg"
                                    fillMode: Image.PreserveAspectFit
                                }
                            }
                        }

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: modelData.name
                            color: Theme.textPrimary
                            font.pixelSize: Theme.fontSizeHeading
                            font.bold: true
                            font.family: Theme.fontFamily
                            elide: Text.ElideRight
                            width: parent.width
                            horizontalAlignment: Text.AlignHCenter
                        }

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: modelData.grade
                            color: Theme.textSecondary
                            font.pixelSize: Theme.fontSizeCaption
                            font.family: Theme.fontFamily
                        }

                        Item { width: 1; height: 4 }

                        PrimaryButton {
                            anchors.horizontalCenter: parent.horizontalCenter
                            width: parent.width
                            preferredHeight: 44
                            text: "Continue →"
                            buttonColor: modelData.isActive ? Theme.primary : Theme.surfaceActive
                            textColor: modelData.isActive ? Theme.textOnPrimary : Theme.textPrimary
                            onClicked: profileController.selectProfile(modelData.index)
                        }
                    }
                }
            }

            // Create New Profile Card (if less than 3 profiles)
            AppCard {
                width: 170
                height: 240
                interactive: true
                visible: profileController.canAddProfile
                onClicked: appController.navigate("create_profile")

                Column {
                    anchors.centerIn: parent
                    spacing: 12
                    width: parent.width - 24

                    Rectangle {
                        width: 60
                        height: 60
                        radius: 30
                        color: Theme.surfaceActive
                        border.color: Theme.primary
                        border.width: 1
                        anchors.horizontalCenter: parent.horizontalCenter

                        Image {
                            anchors.centerIn: parent
                            width: 28
                            height: 28
                            source: "../icons/plus.svg"
                            fillMode: Image.PreserveAspectFit
                        }
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Create\nNew Profile"
                        color: Theme.primaryDark
                        font.pixelSize: Theme.fontSizeBody
                        font.bold: true
                        font.family: Theme.fontFamily
                        horizontalAlignment: Text.AlignHCenter
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: (3 - profileController.profileCount) + " slot(s) free"
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontSizeCaption
                    }
                }
            }
        }
    }

    // PIN unlock modal overlay
    PinModal {
        visible: profileController.pinLocked
        profileName: profileController.pinProfileName
        errorMessage: profileController.pinError
        onPinSubmitted: function(enteredPin) {
            profileController.submitPin(enteredPin);
        }
        onCancelled: profileController.cancelPin()
    }
}
