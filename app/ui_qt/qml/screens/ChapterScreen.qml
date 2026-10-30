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
                title: libraryController.selectedSubject
                networkText: appController.networkLabel
                syncText: appController.syncLabel
                isOnline: appController.isOnline
                showBack: true
                onBackClicked: appController.navigate("subjects")
            }

            // Scrollable Chapters List
            ListView {
                width: parent.width
                height: parent.height - Theme.headerHeight
                clip: true
                spacing: 8
                topMargin: 8
                bottomMargin: 16

                model: libraryController.chapters

                delegate: Item {
                    width: parent.width
                    height: 58

                    AppCard {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: parent.width - 32
                        height: 54
                        interactive: true
                        onClicked: libraryController.selectChapter(modelData)

                        Row {
                            anchors.fill: parent
                            anchors.leftMargin: 18
                            anchors.rightMargin: 18

                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData
                                color: Theme.textPrimary
                                font.pixelSize: Theme.fontSizeBody
                                font.bold: true
                                font.family: Theme.fontFamily
                            }

                            Item { Layout.fillWidth: true; width: 1 }

                            Image {
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                width: 20
                                height: 20
                                source: "../icons/chevron_right.svg"
                            }
                        }
                    }
                }
            }
        }
    }
}
