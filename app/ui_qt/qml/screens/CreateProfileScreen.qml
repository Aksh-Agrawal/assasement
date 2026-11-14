import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.background

    property string profileName: ""
    property string selectedGrade: "Primary 6"

    AppHeader {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        title: "New Student Profile"
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

        AppCard {
            anchors.centerIn: parent
            width: 500
            implicitHeight: contentCol.implicitHeight + Spacing.xl * 2

            Column {
                id: contentCol
                anchors.centerIn: parent
                width: parent.width - Spacing.xl * 2
                spacing: Spacing.md

                Row {
                    spacing: Spacing.sm
                    Rectangle {
                        width: 36
                        height: 36
                        radius: 18
                        color: Theme.softSage
                        Image {
                            anchors.centerIn: parent
                            width: 20
                            height: 20
                            source: Assets.account
                            fillMode: Image.PreserveAspectFit
                        }
                    }
                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        Text {
                            text: "Student Profile Details"
                            color: Theme.textPrimary
                            font.pixelSize: Typography.pageTitle
                            font.family: Typography.fontSerif
                            font.bold: true
                        }
                        Text {
                            text: "Personalize your learning space"
                            color: Theme.textSecondary
                            font.pixelSize: Typography.caption
                            font.family: Typography.fontFamily
                        }
                    }
                }

                // Name field input area
                Column {
                    spacing: Spacing.xs
                    width: parent.width

                    Text {
                        text: "Student Name"
                        color: Theme.textSecondary
                        font.pixelSize: Typography.caption
                        font.family: Typography.fontFamily
                        font.bold: true
                    }

                    Rectangle {
                        width: parent.width
                        height: Metrics.touchNormal
                        radius: Metrics.radiusSm
                        color: Theme.surfaceActive
                        border.color: nameInput.activeFocus ? Theme.forest : Theme.border
                        border.width: nameInput.activeFocus ? 2 : 1

                        Item {
                            anchors.fill: parent
                            anchors.leftMargin: Spacing.md
                            anchors.rightMargin: Spacing.sm
                            anchors.topMargin: Spacing.xs
                            anchors.bottomMargin: Spacing.xs

                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.left: parent.left
                                text: "Type student name here..."
                                color: Theme.textSecondary
                                font.pixelSize: Typography.body
                                font.family: Typography.fontFamily
                                visible: nameInput.text.length === 0
                            }

                            TextInput {
                                id: nameInput
                                anchors.left: parent.left
                                anchors.right: kbBtn.left
                                anchors.rightMargin: Spacing.xs
                                anchors.top: parent.top
                                anchors.bottom: parent.bottom
                                verticalAlignment: TextInput.AlignVCenter
                                text: root.profileName
                                color: Theme.textPrimary
                                font.pixelSize: Typography.body
                                font.family: Typography.fontFamily
                                font.bold: true
                                focus: true
                                selectByMouse: true
                                onTextChanged: {
                                    root.profileName = text;
                                }
                                onAccepted: {
                                    if (createButton.enabled) {
                                        profileController.createProfile(root.profileName, root.selectedGrade);
                                    }
                                }
                            }

                            Rectangle {
                                id: kbBtn
                                width: 36
                                height: 36
                                radius: 18
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                color: kbMouse.containsPress ? Theme.softSage : Theme.surfaceWarm
                                border.color: Theme.border
                                border.width: 1

                                Image {
                                    anchors.centerIn: parent
                                    source: Assets.keyboard
                                    width: 20
                                    height: 20
                                    fillMode: Image.PreserveAspectFit
                                }

                                MouseArea {
                                    id: kbMouse
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        appController.openKeyboard("profile_name", root.profileName, false, "Enter Student Name");
                                    }
                                }
                            }
                        }
                    }
                }

                // Grade selection
                Column {
                    spacing: Spacing.xs
                    width: parent.width

                    Text {
                        text: "Class / Grade Level"
                        color: Theme.textSecondary
                        font.pixelSize: Typography.caption
                        font.family: Typography.fontFamily
                        font.bold: true
                    }

                    Row {
                        spacing: Spacing.sm
                        Repeater {
                            model: ["Primary 4", "Primary 5", "Primary 6", "Secondary 1"]
                            delegate: Rectangle {
                                width: (contentCol.width - Spacing.sm * 3) / 4
                                height: 44
                                radius: Metrics.radiusSm
                                color: root.selectedGrade === modelData ? Theme.forest : Theme.surfaceActive
                                border.color: root.selectedGrade === modelData ? Theme.forest : Theme.border
                                border.width: 1

                                Text {
                                    anchors.centerIn: parent
                                    text: modelData
                                    font.pixelSize: Typography.metadata
                                    font.bold: root.selectedGrade === modelData
                                    font.family: Typography.fontFamily
                                    color: root.selectedGrade === modelData ? Theme.paper : Theme.textPrimary
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.selectedGrade = modelData
                                }
                            }
                        }
                    }
                }

                Item { width: 1; height: Spacing.xs }

                PrimaryButton {
                    id: createButton
                    width: parent.width
                    preferredHeight: Metrics.touchNormal
                    text: "Create Study Profile"
                    enabled: profileController.canAddProfile && !settingsController.accountActionBusy
                             && root.profileName.trim().length > 0
                    onClicked: {
                        profileController.createProfile(root.profileName, root.selectedGrade);
                    }
                }
            }
        }
    }

    // Connect to keyboard submission
    Connections {
        target: appController
        function onKeyboardSubmitted(text) {
            if (appController.keyboardTarget === "profile_name") {
                root.profileName = text;
                nameInput.text = text;
            }
        }
    }
}
