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
        title: "Create Study Profile"
        networkText: appController.networkLabel
        syncText: appController.syncLabel
        isOnline: appController.isOnline
        showBack: true
        onBackClicked: appController.navigate("profile_picker")
    }

    AppCard {
        anchors.centerIn: parent
        anchors.verticalCenterOffset: 10
        width: 480
        implicitHeight: contentCol.implicitHeight + 36

        Column {
            id: contentCol
            anchors.centerIn: parent
            width: parent.width - 48
            spacing: 14

            Text {
                text: "Profile Details"
                color: Theme.textPrimary
                font.pixelSize: Theme.fontSizeHeading
                font.bold: true
                font.family: Theme.fontFamily
            }

            // Name field tap area
            Column {
                spacing: 4
                width: parent.width

                Text {
                    text: "Student Name"
                    color: Theme.textSecondary
                    font.pixelSize: Theme.fontSizeCaption
                }

                Rectangle {
                    width: parent.width
                    height: 52
                    radius: 10
                    color: Theme.surfaceActive
                    border.color: nameMouse.containsPress ? Theme.primary : Theme.border
                    border.width: 1

                    Text {
                        anchors.left: parent.left
                        anchors.leftMargin: 14
                        anchors.verticalCenter: parent.verticalCenter
                        text: root.profileName.length > 0 ? root.profileName : "Tap to enter name..."
                        color: root.profileName.length > 0 ? Theme.textPrimary : Theme.textSecondary
                        font.pixelSize: Theme.fontSizeBody
                    }

                    MouseArea {
                        id: nameMouse
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            appController.openKeyboard("profile_name", root.profileName, false, "Enter Profile Name");
                        }
                    }
                }
            }

            // Grade selection
            Column {
                spacing: 6
                width: parent.width

                Text {
                    text: "Class / Grade"
                    color: Theme.textSecondary
                    font.pixelSize: Theme.fontSizeCaption
                }

                Row {
                    spacing: 8
                    Repeater {
                        model: ["Primary 4", "Primary 5", "Primary 6", "Secondary 1"]
                        delegate: Rectangle {
                            width: (contentCol.width - 24) / 4
                            height: 44
                            radius: 8
                            color: root.selectedGrade === modelData ? Theme.primaryLight : Theme.surfaceActive
                            border.color: root.selectedGrade === modelData ? Theme.primary : Theme.border
                            border.width: root.selectedGrade === modelData ? 2 : 1

                            Text {
                                anchors.centerIn: parent
                                text: modelData
                                font.pixelSize: 13
                                font.bold: root.selectedGrade === modelData
                                color: root.selectedGrade === modelData ? Theme.primaryDark : Theme.textPrimary
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: root.selectedGrade = modelData
                            }
                        }
                    }
                }
            }

            Item { width: 1; height: 8 }

            PrimaryButton {
                width: parent.width
                preferredHeight: Theme.touchNormal
                text: "Save Profile"
                enabled: root.profileName.trim().length > 0
                onClicked: {
                    profileController.createProfile(root.profileName, root.selectedGrade);
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
            }
        }
    }
}
