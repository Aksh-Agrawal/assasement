import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.background

    Row {
        anchors.fill: parent

        // Left Navigation Rail
        NavRail {
            id: rail
            height: parent.height
            currentTab: "home"
            onTabSelected: function(tab) {
                if (tab === "home") appController.navigate("home");
                else if (tab === "library") appController.navigate("subjects");
                else if (tab === "practice") appController.navigate("content");
                else if (tab === "history") appController.navigate("history");
                else if (tab === "settings") appController.navigate("settings");
            }
        }

        // Main Content Area
        Column {
            width: parent.width - rail.width
            height: parent.height

            AppHeader {
                width: parent.width
                allowProfileSwitch: true
                onSwitchProfileClicked: profileController.switchProfile()
                profileText: appController.activeProfileName + (appController.activeProfileGrade.length > 0 ? " • " + appController.activeProfileGrade : "")
                networkText: appController.networkLabel
                syncText: appController.syncLabel
                isOnline: appController.isOnline
            }

            // Scrollable / Responsive Content Body
            Item {
                width: parent.width
                height: parent.height - Theme.headerHeight

                Column {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 12

                    // Greeting
                    Column {
                        spacing: 2
                        Text {
                            text: "Good day, " + appController.activeProfileName + "!"
                            color: Theme.textPrimary
                            font.pixelSize: Theme.fontSizeTitle
                            font.bold: true
                            font.family: Theme.fontFamily
                        }
                        Text {
                            text: "Ready to explore and practice today?"
                            color: Theme.textSecondary
                            font.pixelSize: Theme.fontSizeSecondary
                            font.family: Theme.fontFamily
                        }
                    }

                    // Continue Practice Hero Card
                    AppCard {
                        width: parent.width
                        height: 150
                        interactive: libraryController.canResume
                        onClicked: {
                            if (libraryController.canResume) {
                                assessmentController.resumeTest();
                            }
                        }

                        Row {
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 16

                            // Card icon
                            Rectangle {
                                width: 54
                                height: 54
                                radius: 14
                                color: libraryController.canResume ? Theme.primaryLight : Theme.surfaceActive
                                anchors.verticalCenter: parent.verticalCenter

                                Image {
                                    anchors.centerIn: parent
                                    width: 28
                                    height: 28
                                    source: libraryController.canResume ? Assets.practice : Assets.library
                                    fillMode: Image.PreserveAspectFit
                                }
                            }

                            // Card details
                            Column {
                                width: parent.width - 54 - 16 - 150
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 6

                                Text {
                                    text: libraryController.canResume ? "Continue Practice" : "Start New Practice"
                                    color: Theme.textSecondary
                                    font.pixelSize: Theme.fontSizeCaption
                                    font.bold: true
                                    font.family: Theme.fontFamily
                                }

                                Text {
                                    text: libraryController.canResume ? libraryController.resumeTitle : "Choose a topic from the library"
                                    color: Theme.textPrimary
                                    font.pixelSize: Theme.fontSizeHeading
                                    font.bold: true
                                    font.family: Theme.fontFamily
                                    elide: Text.ElideRight
                                    width: parent.width
                                }

                                Row {
                                    spacing: 12
                                    visible: libraryController.canResume
                                    ProgressBar {
                                        width: 180
                                        height: 10
                                        progress: libraryController.resumeTotal > 0 ? (libraryController.resumeAnswered / libraryController.resumeTotal) : 0
                                    }
                                    Text {
                                        text: libraryController.resumeAnswered + " of " + libraryController.resumeTotal + " answered"
                                        color: Theme.textSecondary
                                        font.pixelSize: Theme.fontSizeCaption
                                        font.family: Theme.fontFamily
                                    }
                                }
                            }

                            // Continue / Browse Action Button
                            PrimaryButton {
                                anchors.verticalCenter: parent.verticalCenter
                                preferredHeight: Theme.touchNormal
                                text: libraryController.canResume ? "Continue →" : "Browse →"
                                onClicked: {
                                    if (libraryController.canResume) {
                                        assessmentController.resumeTest();
                                    } else {
                                        appController.navigate("subjects");
                                    }
                                }
                            }
                        }
                    }

                    // Quick Action Buttons
                    Row {
                        width: parent.width
                        spacing: 12

                        AppCard {
                            width: (parent.width - 24) / 3
                            height: 80
                            interactive: true
                            onClicked: appController.navigate("subjects")

                            Row {
                                anchors.centerIn: parent
                                spacing: 12
                                Rectangle {
                                    width: 40; height: 40; radius: 20
                                    color: Theme.primaryLight
                                    Image {
                                        anchors.centerIn: parent; width: 20; height: 20
                                        source: Assets.library
                                    }
                                }
                                Column {
                                    anchors.verticalCenter: parent.verticalCenter
                                    Text { text: "Browse Library"; font.bold: true; font.pixelSize: 15; color: Theme.textPrimary }
                                    Text { text: "All subjects"; font.pixelSize: 12; color: Theme.textSecondary }
                                }
                            }
                        }

                        AppCard {
                            width: (parent.width - 24) / 3
                            height: 80
                            interactive: true
                            onClicked: appController.navigate("content")

                            Row {
                                anchors.centerIn: parent
                                spacing: 12
                                Rectangle {
                                    width: 40; height: 40; radius: 20
                                    color: "#FFF3E0"
                                    Image {
                                        anchors.centerIn: parent; width: 20; height: 20
                                        source: Assets.download
                                    }
                                }
                                Column {
                                    anchors.verticalCenter: parent.verticalCenter
                                    Text { text: "Downloads"; font.bold: true; font.pixelSize: 15; color: Theme.textPrimary }
                                    Text { text: "Offline packs"; font.pixelSize: 12; color: Theme.textSecondary }
                                }
                            }
                        }

                        AppCard {
                            width: (parent.width - 24) / 3
                            height: 80
                            interactive: true
                            onClicked: appController.navigate("history")

                            Row {
                                anchors.centerIn: parent
                                spacing: 12
                                Rectangle {
                                    width: 40; height: 40; radius: 20
                                    color: "#E8F5E9"
                                    Image {
                                        anchors.centerIn: parent; width: 20; height: 20
                                        source: Assets.history
                                    }
                                }
                                Column {
                                    anchors.verticalCenter: parent.verticalCenter
                                    Text { text: "Past Attempts"; font.bold: true; font.pixelSize: 15; color: Theme.textPrimary }
                                    Text { text: "Scores & review"; font.pixelSize: 12; color: Theme.textSecondary }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
