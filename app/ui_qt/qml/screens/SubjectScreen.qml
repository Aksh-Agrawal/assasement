import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.background

    Row {
        anchors.fill: parent

        NavRail {
            id: rail
            height: parent.height
            currentTab: "library"
            onTabSelected: function(tab) {
                if (tab === "home") appController.navigate("home");
                else if (tab === "library") appController.navigate("subjects");
                else if (tab === "practice") appController.navigate("content");
                else if (tab === "history") appController.navigate("history");
                else if (tab === "settings") appController.navigate("settings");
            }
        }

        Column {
            width: parent.width - rail.width
            height: parent.height

            AppHeader {
                width: parent.width
                title: "Choose a Subject"
                networkText: appController.networkLabel
                syncText: appController.syncLabel
                isOnline: appController.isOnline
                showBack: true
                onBackClicked: appController.navigate("home")
            }

            Item {
                width: parent.width
                height: parent.height - Theme.headerHeight

                EmptyState {
                    anchors.centerIn: parent
                    visible: libraryController.subjects.length === 0
                    title: "No Subjects Available"
                    description: "Connect to Wi-Fi to sync your curriculum catalogue."
                    actionText: "Back to Home"
                    onActionClicked: appController.navigate("home")
                }

                Grid {
                    anchors.centerIn: parent
                    columns: 2
                    spacing: 16
                    visible: libraryController.subjects.length > 0

                    Repeater {
                        model: libraryController.subjects

                        delegate: AppCard {
                            width: 320
                            height: 140
                            interactive: true
                            onClicked: libraryController.selectSubject(modelData)

                            Row {
                                anchors.fill: parent
                                anchors.margins: 16
                                spacing: 16

                                Rectangle {
                                    width: 60
                                    height: 60
                                    radius: 16
                                    color: {
                                        if (modelData === "Mathematics") return "#E0F2F1";
                                        if (modelData === "Science") return "#FFEBEE";
                                        if (modelData === "English") return "#FFF3E0";
                                        return Theme.primaryLight;
                                    }
                                    anchors.verticalCenter: parent.verticalCenter

                                    Image {
                                        anchors.centerIn: parent
                                        width: 32
                                        height: 32
                                        source: {
                                            if (modelData === "Mathematics") return Assets.calculator;
                                            if (modelData === "Science") return Assets.flask;
                                            return Assets.library;
                                        }
                                        fillMode: Image.PreserveAspectFit
                                    }
                                }

                                Column {
                                    width: parent.width - 60 - 16 - 24
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 4

                                    Text {
                                        text: modelData
                                        color: Theme.textPrimary
                                        font.pixelSize: Theme.fontSizeHeading
                                        font.bold: true
                                        font.family: Theme.fontFamily
                                    }

                                    Text {
                                        text: {
                                            if (modelData === "Mathematics") return "Numbers, shapes & operations";
                                            if (modelData === "Science") return "Living world, materials & forces";
                                            if (modelData === "English") return "Grammar, comprehension & vocabulary";
                                            return "General learning topics";
                                        }
                                        color: Theme.textSecondary
                                        font.pixelSize: Theme.fontSizeCaption
                                        font.family: Theme.fontFamily
                                        wrapMode: Text.Wrap
                                        width: parent.width
                                    }
                                }

                                Image {
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: 20
                                    height: 20
                                    source: Assets.chevron_right
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
