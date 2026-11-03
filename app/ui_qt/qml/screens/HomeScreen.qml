import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.canvas

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
                height: parent.height - Metrics.headerHeight

                Column {
                    anchors.fill: parent
                    anchors.leftMargin: Spacing.lg
                    anchors.rightMargin: Spacing.lg
                    anchors.topMargin: Spacing.xs
                    anchors.bottomMargin: Spacing.md
                    spacing: Spacing.md

                    // -------------------------------------------------------------
                    // HERO SECTION (Contextual: In-Progress vs Fresh Practice)
                    // -------------------------------------------------------------
                    AppCard {
                        width: parent.width
                        height: 230
                        interactive: false

                        // Content row inside Hero
                        Row {
                            anchors.fill: parent
                            anchors.margins: Spacing.lg
                            spacing: Spacing.lg

                            // Left Text & Action Column
                            Column {
                                width: parent.width - 240
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: Spacing.sm

                                // Badge / Context Label
                                Rectangle {
                                    height: 24
                                    width: heroBadgeText.implicitWidth + 16
                                    radius: 12
                                    color: libraryController.canResume ? Theme.terracottaLight : Theme.primaryLight
                                    border.color: libraryController.canResume ? Theme.terracotta : Theme.sage
                                    border.width: 1

                                    Text {
                                        id: heroBadgeText
                                        anchors.centerIn: parent
                                        text: libraryController.canResume ? "● In Progress" : "Daily Practice"
                                        color: libraryController.canResume ? Theme.terracotta : Theme.forest
                                        font.pixelSize: Typography.caption
                                        font.bold: true
                                        font.family: Typography.family
                                    }
                                }

                                // Greeting / Resume Title
                                Text {
                                    text: libraryController.canResume ? ("Continue " + libraryController.resumeTitle) : ("Good morning, " + appController.activeProfileName)
                                    color: Theme.deepInk
                                    font.pixelSize: Typography.pageTitle
                                    font.bold: true
                                    font.family: Typography.familyEditorial
                                    elide: Text.ElideRight
                                    width: parent.width
                                }

                                // Subtext
                                Text {
                                    text: libraryController.canResume ? (libraryController.resumeAnswered + " of " + libraryController.resumeTotal + " questions complete") : "Ready for today's practice? Choose a topic to begin."
                                    color: Theme.mutedInk
                                    font.pixelSize: Typography.body
                                    font.family: Typography.family
                                    wrapMode: Text.Wrap
                                    width: parent.width
                                }

                                // Progress rail if resuming
                                Row {
                                    spacing: Spacing.sm
                                    visible: libraryController.canResume
                                    ProgressBar {
                                        width: 180
                                        height: 8
                                        barColor: Theme.terracotta
                                        progress: libraryController.resumeTotal > 0 ? (libraryController.resumeAnswered / libraryController.resumeTotal) : 0
                                    }
                                    Text {
                                        text: (libraryController.resumeTotal > 0 ? Math.round((libraryController.resumeAnswered / libraryController.resumeTotal) * 100) : 0) + "%"
                                        color: Theme.mutedInk
                                        font.pixelSize: Typography.caption
                                        font.bold: true
                                        font.family: Typography.family
                                    }
                                }

                                Item { width: 1; height: Spacing.xs }

                                // ONE Strong Primary Action Button
                                PrimaryButton {
                                    preferredHeight: Metrics.touchNormal
                                    buttonColor: libraryController.canResume ? Theme.forest : Theme.forest
                                    text: libraryController.canResume ? "Continue Practice →" : "Start Practice →"
                                    onClicked: {
                                        if (libraryController.canResume) {
                                            assessmentController.resumeTest();
                                        } else {
                                            appController.navigate("subjects");
                                        }
                                    }
                                }
                            }

                            // Right Hero Artwork
                            Image {
                                width: 220
                                height: 180
                                anchors.verticalCenter: parent.verticalCenter
                                source: libraryController.canResume ? Assets.home_resume : Assets.home_hero
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                            }
                        }
                    }

                    // -------------------------------------------------------------
                    // SECONDARY DESTINATIONS: Illustrated Subject Cards
                    // -------------------------------------------------------------
                    Row {
                        width: parent.width
                        spacing: Spacing.md

                        // Biology
                        AppCard {
                            width: (parent.width - Spacing.md * 2) / 3
                            height: 125
                            interactive: true
                            onClicked: libraryController.selectSubject("Biology")

                            Row {
                                anchors.fill: parent
                                anchors.margins: Spacing.md
                                spacing: Spacing.md

                                Image {
                                    width: 48
                                    height: 48
                                    anchors.verticalCenter: parent.verticalCenter
                                    source: Assets.biology
                                    fillMode: Image.PreserveAspectFit
                                }

                                Column {
                                    width: parent.width - 48 - Spacing.md
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 3

                                    Text {
                                        text: "Biology"
                                        font.bold: true
                                        font.pixelSize: Typography.body
                                        color: Theme.deepInk
                                        font.family: Typography.family
                                    }
                                    Text {
                                        text: "Cells • Genetics • Physiology"
                                        font.pixelSize: Typography.caption
                                        color: Theme.mutedInk
                                        elide: Text.ElideRight
                                        width: parent.width
                                    }
                                    Text {
                                        text: "Practice →"
                                        font.pixelSize: 11
                                        font.bold: true
                                        color: Theme.forest
                                    }
                                }
                            }
                        }

                        // Chemistry
                        AppCard {
                            width: (parent.width - Spacing.md * 2) / 3
                            height: 125
                            interactive: true
                            onClicked: libraryController.selectSubject("Chemistry")

                            Row {
                                anchors.fill: parent
                                anchors.margins: Spacing.md
                                spacing: Spacing.md

                                Image {
                                    width: 48
                                    height: 48
                                    anchors.verticalCenter: parent.verticalCenter
                                    source: Assets.chemistry
                                    fillMode: Image.PreserveAspectFit
                                }

                                Column {
                                    width: parent.width - 48 - Spacing.md
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 3

                                    Text {
                                        text: "Chemistry"
                                        font.bold: true
                                        font.pixelSize: Typography.body
                                        color: Theme.deepInk
                                        font.family: Typography.family
                                    }
                                    Text {
                                        text: "Atoms • Bonding • Reactions"
                                        font.pixelSize: Typography.caption
                                        color: Theme.mutedInk
                                        elide: Text.ElideRight
                                        width: parent.width
                                    }
                                    Text {
                                        text: "Practice →"
                                        font.pixelSize: 11
                                        font.bold: true
                                        color: Theme.terracotta
                                    }
                                }
                            }
                        }

                        // Mathematics
                        AppCard {
                            width: (parent.width - Spacing.md * 2) / 3
                            height: 125
                            interactive: true
                            onClicked: libraryController.selectSubject("Mathematics")

                            Row {
                                anchors.fill: parent
                                anchors.margins: Spacing.md
                                spacing: Spacing.md

                                Image {
                                    width: 48
                                    height: 48
                                    anchors.verticalCenter: parent.verticalCenter
                                    source: Assets.mathematics
                                    fillMode: Image.PreserveAspectFit
                                }

                                Column {
                                    width: parent.width - 48 - Spacing.md
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 3

                                    Text {
                                        text: "Mathematics"
                                        font.bold: true
                                        font.pixelSize: Typography.body
                                        color: Theme.deepInk
                                        font.family: Typography.family
                                    }
                                    Text {
                                        text: "Numbers • Algebra • Geometry"
                                        font.pixelSize: Typography.caption
                                        color: Theme.mutedInk
                                        elide: Text.ElideRight
                                        width: parent.width
                                    }
                                    Text {
                                        text: "Practice →"
                                        font.pixelSize: 11
                                        font.bold: true
                                        color: Theme.gold
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
