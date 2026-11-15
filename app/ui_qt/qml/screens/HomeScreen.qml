import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.canvas
    readonly property bool hasPractice: libraryController.canResume || subjects.count > 0

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
                else if (tab === "progress") appController.navigate("progress");
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
            Flickable {
                width: parent.width
                height: parent.height - Metrics.headerHeight
                contentWidth: width
                contentHeight: body.height + Spacing.md
                clip: true
                boundsBehavior: Flickable.StopAtBounds

                Column {
                    id: body
                    x: Spacing.lg
                    y: Spacing.xs
                    width: parent.width - 2 * Spacing.lg
                    spacing: Spacing.md

                    // -------------------------------------------------------------
                    // HERO SECTION (Contextual: In-Progress vs Fresh Practice)
                    // -------------------------------------------------------------
                    AppCard {
                        width: parent.width
                        height: 208
                        customBgColor: Theme.surfaceElevated
                        interactive: false

                        // Content row inside Hero
                        Row {
                            anchors.fill: parent
                            anchors.margins: Spacing.lg
                            spacing: Spacing.lg

                            // Left Text & Action Column
                            Column {
                                width: parent.width - (art.visible ? art.width + Spacing.lg : 0)
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: Spacing.sm

                                Text {
                                    text: libraryController.canResume ? "Practice in progress" : "Your study desk"
                                    color: Theme.forest
                                    font.pixelSize: Typography.metadata
                                    font.bold: true
                                    font.family: Typography.family
                                }

                                // Greeting / Resume Title
                                Text {
                                    objectName: "homeGreeting"
                                    text: libraryController.canResume ? ("Continue " + libraryController.resumeTitle) : (appController.greeting + ", " + appController.activeProfileName)
                                    color: Theme.deepInk
                                    font.pixelSize: Typography.hero
                                    font.bold: true
                                    font.family: Typography.familyEditorial
                                    elide: Text.ElideRight
                                    width: parent.width
                                }

                                // Subtext
                                Text {
                                    visible: root.hasPractice
                                    text: libraryController.canResume ? (libraryController.resumeAnswered + " of " + libraryController.resumeTotal + " questions answered") : "Choose a subject to pick up a practice set."
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

                                Item { width: 1; height: Spacing.xs; visible: root.hasPractice }

                                // ONE Strong Primary Action Button
                                PrimaryButton {
                                    visible: root.hasPractice
                                    preferredHeight: Metrics.touchNormal
                                    buttonColor: Theme.forest
                                    text: libraryController.canResume ? "Continue practice" : "Choose a subject"
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
                                id: art
                                visible: parent.width >= 460
                                width: 196
                                height: 180
                                sourceSize: Qt.size(width, height)
                                anchors.verticalCenter: parent.verticalCenter
                                source: libraryController.canResume ? Assets.home_resume : Assets.home_hero
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                            }
                        }
                    }

                    LibraryCard {
                        objectName: "homeSoftwareUpdateReminder"
                        visible: settingsController.updateReminderVersion.length > 0
                        width: parent.width
                        height: 76
                        title: "Software update available"
                        context: "Version " + settingsController.updateReminderVersion
                        actionText: "View update"
                        iconSource: Assets.update
                        onClicked: settingsController.viewUpdateNotice()
                    }

                    LibraryGrid {
                        id: subjects
                        width: parent.width
                        height: Math.ceil(count / columns) * cellHeight
                        columns: count >= 3 && width >= 620 ? 3 : 2
                        cardHeight: 88
                        interactive: false
                        visible: count > 0
                        model: libraryController.homeSubjects

                        delegate: SubjectCard {
                            required property var modelData
                            width: subjects.cellWidth - Spacing.sm
                            height: subjects.cardHeight
                            subject: modelData.name
                            chapters: modelData.chapters
                            onClicked: libraryController.selectInstalledSubject(modelData.name)
                        }
                    }

                    AppCard {
                        width: parent.width
                        height: emptyCopy.implicitHeight + 2 * Spacing.md
                        visible: subjects.count === 0

                        Column {
                            id: emptyCopy
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: Spacing.md
                            spacing: Spacing.xs

                            Text {
                                width: parent.width
                                text: "No subjects downloaded yet."
                                font.family: Typography.family
                                font.pixelSize: Typography.body
                                font.bold: true
                                color: Theme.deepInk
                                wrapMode: Text.Wrap
                            }

                            Text {
                                width: parent.width
                                text: "Connect to Wi-Fi to explore and download practice questions."
                                font.family: Typography.family
                                font.pixelSize: Typography.caption
                                color: Theme.mutedInk
                                wrapMode: Text.Wrap
                            }

                            SecondaryButton {
                                text: "Practice Library"
                                onClicked: libraryController.openQuestionBanks()
                            }
                        }
                    }
                }
            }
        }
    }
}
