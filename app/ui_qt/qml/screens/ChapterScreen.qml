import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.canvas

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
                else if (tab === "progress") appController.navigate("progress");
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
                profileText: appController.activeProfileName
                networkText: appController.networkLabel
                syncText: appController.syncLabel
                isOnline: appController.isOnline
                showBack: true
                onBackClicked: appController.navigate("subjects")
            }

            // Subject Context Banner
            Rectangle {
                width: parent.width - Spacing.xl
                height: 50
                anchors.horizontalCenter: parent.horizontalCenter
                radius: Metrics.radiusMedium
                color: Theme.subjectLightAccent(libraryController.selectedSubject)
                border.color: Theme.border
                border.width: 1

                Item {
                    anchors.fill: parent
                    anchors.leftMargin: Spacing.md
                    anchors.rightMargin: Spacing.md

                    Row {
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: Spacing.md

                        Image {
                            width: 34
                            height: 34
                            anchors.verticalCenter: parent.verticalCenter
                            source: Theme.subjectIcon(libraryController.selectedSubject)
                            fillMode: Image.PreserveAspectFit
                        }

                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 1

                            Text {
                                text: libraryController.selectedSubject + " Curriculum"
                                color: Theme.deepInk
                                font.pixelSize: Typography.body
                                font.bold: true
                                font.family: Typography.fontFamily
                            }

                            Text {
                                text: "Select a chapter to practice specific learning objectives"
                                color: Theme.mutedInk
                                font.pixelSize: Typography.caption
                                font.family: Typography.fontFamily
                            }
                        }
                    }

                    Rectangle {
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        height: 24
                        width: countText.implicitWidth + 14
                        radius: 12
                        color: Theme.surface
                        border.color: Theme.border
                        border.width: 1

                        Text {
                            id: countText
                            anchors.centerIn: parent
                            text: libraryController.chapters.length + " chapters"
                            color: Theme.deepInk
                            font.pixelSize: Typography.caption
                            font.bold: true
                            font.family: Typography.fontFamily
                        }
                    }
                }
            }

            Item { width: 1; height: Spacing.xs }

            // Empty state if no chapters
            EmptyState {
                anchors.centerIn: parent
                visible: libraryController.chapters.length === 0
                title: "No Topics Available"
                description: "No topics or chapters found for " + libraryController.selectedSubject + "."
                actionText: "Back to Subjects"
                onActionClicked: appController.navigate("subjects")
            }

            // Functional Chapter Ledger Rows
            ListView {
                width: parent.width
                height: parent.height - Metrics.headerHeight - 60
                anchors.margins: Spacing.md
                clip: true
                spacing: Spacing.xs
                topMargin: Spacing.xs
                bottomMargin: Spacing.md
                visible: libraryController.chapters.length > 0
                model: libraryController.chapters

                delegate: Rectangle {
                    width: parent.width - Spacing.xl
                    height: 52
                    anchors.horizontalCenter: parent.horizontalCenter
                    radius: Metrics.radiusSmall
                    color: chapterMouse.containsPress ? Theme.surfaceActive : Theme.surface
                    border.color: Theme.border
                    border.width: 1

                    Behavior on color {
                        ColorAnimation { duration: Theme.animDuration }
                    }

                    Item {
                        anchors.fill: parent
                        anchors.leftMargin: Spacing.lg
                        anchors.rightMargin: Spacing.lg

                        Row {
                            anchors.left: parent.left
                            anchors.right: chevronRow.left
                            anchors.rightMargin: Spacing.md
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: Spacing.md

                            // Bullet accent
                            Rectangle {
                                width: 6
                                height: 6
                                radius: 3
                                color: Theme.subjectAccent(libraryController.selectedSubject)
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            Text {
                                text: modelData
                                color: Theme.deepInk
                                font.pixelSize: Typography.body
                                font.bold: true
                                font.family: Typography.fontFamily
                                elide: Text.ElideRight
                                width: parent.width - 20
                            }
                        }

                        Row {
                            id: chevronRow
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: Spacing.xs

                            Text {
                                text: "Practice sets"
                                color: Theme.mutedInk
                                font.pixelSize: Typography.caption
                                font.family: Typography.fontFamily
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            Image {
                                anchors.verticalCenter: parent.verticalCenter
                                width: 16
                                height: 16
                                source: Assets.chevron_right
                            }
                        }
                    }

                    MouseArea {
                        id: chapterMouse
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: libraryController.selectChapter(modelData)
                    }

                    // Focus ring
                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: -2
                        radius: parent.radius + 2
                        color: "transparent"
                        border.color: Theme.borderFocus
                        border.width: Metrics.borderFocus
                        visible: parent.activeFocus
                    }
                }
            }
        }
    }
}
