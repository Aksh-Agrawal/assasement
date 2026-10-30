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

            // Empty state if no chapters
            EmptyState {
                anchors.centerIn: parent
                visible: libraryController.chapters.length === 0
                title: "No Topics Available"
                description: "No topics or chapters found for " + libraryController.selectedSubject + "."
                actionText: "Back to Subjects"
                onActionClicked: appController.navigate("subjects")
            }

            // Scrollable Chapters List
            ListView {
                width: parent.width
                height: parent.height - Theme.headerHeight
                clip: true
                spacing: 8
                topMargin: 8
                bottomMargin: 16
                visible: libraryController.chapters.length > 0

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

                        Item {
                            anchors.fill: parent
                            anchors.leftMargin: 18
                            anchors.rightMargin: 18

                            Text {
                                anchors.left: parent.left
                                anchors.right: chevronIcon.left
                                anchors.rightMargin: 12
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData
                                color: Theme.textPrimary
                                font.pixelSize: Theme.fontSizeBody
                                font.bold: true
                                font.family: Theme.fontFamily
                                elide: Text.ElideRight
                            }

                            Image {
                                id: chevronIcon
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
