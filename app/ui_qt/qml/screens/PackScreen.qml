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
                title: libraryController.selectedChapter.length > 0 ? libraryController.selectedChapter : libraryController.selectedSubject
                networkText: appController.networkLabel
                syncText: appController.syncLabel
                isOnline: appController.isOnline
                showBack: true
                onBackClicked: appController.navigate("chapters")
            }

            ListView {
                width: parent.width
                height: parent.height - Theme.headerHeight
                clip: true
                spacing: 10
                topMargin: 8
                bottomMargin: 16

                model: libraryController.packs

                delegate: Item {
                    width: parent.width
                    height: 74

                    AppCard {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: parent.width - 32
                        height: 70
                        interactive: true
                        onClicked: {
                            if (modelData.isInstalled) {
                                libraryController.selectPack(modelData.id, modelData.version);
                            } else {
                                libraryController.downloadPack(modelData.id, modelData.version);
                            }
                        }

                        Row {
                            anchors.fill: parent
                            anchors.leftMargin: 18
                            anchors.rightMargin: 18
                            spacing: 14

                            Rectangle {
                                width: 44
                                height: 44
                                radius: 12
                                color: modelData.isInstalled ? Theme.primaryLight : "#FFF3E0"
                                anchors.verticalCenter: parent.verticalCenter

                                Image {
                                    anchors.centerIn: parent
                                    width: 22
                                    height: 22
                                    source: modelData.isInstalled ? "../icons/practice.svg" : "../icons/download.svg"
                                    fillMode: Image.PreserveAspectFit
                                }
                            }

                            Column {
                                width: parent.width - 44 - 14 - 140
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 4

                                Row {
                                    spacing: 8
                                    Text {
                                        text: modelData.title
                                        color: Theme.textPrimary
                                        font.pixelSize: Theme.fontSizeBody
                                        font.bold: true
                                        font.family: Theme.fontFamily
                                        elide: Text.ElideRight
                                    }

                                    StatusBadge {
                                        text: modelData.badge
                                        statusType: modelData.badge === "Official" ? "success" : "neutral"
                                        implicitHeight: 22
                                    }
                                }

                                Text {
                                    text: modelData.questionCount + " questions" + (modelData.isInstalled ? " • Ready on this device" : " • Available for download")
                                    color: Theme.textSecondary
                                    font.pixelSize: Theme.fontSizeCaption
                                    font.family: Theme.fontFamily
                                }
                            }

                            PrimaryButton {
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                preferredHeight: 46
                                text: modelData.isInstalled ? "Practice →" : "Download"
                                buttonColor: modelData.isInstalled ? Theme.primary : Theme.surfaceActive
                                textColor: modelData.isInstalled ? Theme.textOnPrimary : Theme.textPrimary
                                onClicked: {
                                    if (modelData.isInstalled) {
                                        libraryController.selectPack(modelData.id, modelData.version);
                                    } else {
                                        libraryController.downloadPack(modelData.id, modelData.version);
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
