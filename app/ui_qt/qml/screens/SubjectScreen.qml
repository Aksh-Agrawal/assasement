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
                else if (tab === "history") appController.navigate("history");
                else if (tab === "settings") appController.navigate("settings");
            }
        }

        Column {
            width: parent.width - rail.width
            height: parent.height

            AppHeader {
                width: parent.width
                title: "Practice Library"
                profileText: appController.activeProfileName
                networkText: appController.networkLabel
                syncText: appController.syncLabel
                isOnline: appController.isOnline
                showBack: true
                onBackClicked: appController.navigate("home")
            }

            Item {
                width: parent.width
                height: parent.height - Metrics.headerHeight

                EmptyState {
                    anchors.centerIn: parent
                    visible: libraryController.subjects.length === 0
                    title: "No Subjects Available"
                    description: "Connect to Wi-Fi to sync your curriculum catalogue."
                    actionText: "Back to Home"
                    onActionClicked: appController.navigate("home")
                }

                // Illustrated Subject Bookshelf List
                ListView {
                    width: parent.width
                    height: parent.height
                    anchors.margins: Spacing.md
                    clip: true
                    spacing: Spacing.sm
                    topMargin: Spacing.xs
                    bottomMargin: Spacing.md
                    visible: libraryController.subjects.length > 0
                    model: libraryController.subjects

                    delegate: Item {
                        width: parent.width
                        height: 76

                        AppCard {
                            anchors.horizontalCenter: parent.horizontalCenter
                            width: parent.width - Spacing.xl
                            height: 70
                            interactive: true
                            onClicked: libraryController.selectSubject(modelData)

                            Item {
                                anchors.fill: parent
                                anchors.leftMargin: Spacing.md
                                anchors.rightMargin: Spacing.lg

                                Row {
                                    anchors.left: parent.left
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: Spacing.md

                                    // Subject Art Medallion
                                    Image {
                                        width: 48
                                        height: 48
                                        anchors.verticalCenter: parent.verticalCenter
                                        source: Theme.subjectIcon(modelData)
                                        fillMode: Image.PreserveAspectFit
                                    }

                                    // Subject Title & Curated Topic List
                                    Column {
                                        width: 420
                                        anchors.verticalCenter: parent.verticalCenter
                                        spacing: 3

                                        Text {
                                            text: modelData
                                            color: Theme.deepInk
                                            font.pixelSize: Typography.sectionTitle
                                            font.bold: true
                                            font.family: Typography.fontFamily
                                        }

                                        Text {
                                            text: {
                                                var s = modelData.toLowerCase();
                                                if (s.indexOf("bio") !== -1) return "Cells • Genetics • Physiology • Plant Systems";
                                                if (s.indexOf("chem") !== -1) return "Atoms • Chemical Bonding • Organic Reactions";
                                                if (s.indexOf("math") !== -1) return "Numbers • Algebra • Geometry • Functions";
                                                if (s.indexOf("sci") !== -1) return "Forces & Energy • Electricity • Living World";
                                                if (s.indexOf("eng") !== -1) return "Comprehension • Grammar & Vocabulary";
                                                return "Curriculum practice & assessment sets";
                                            }
                                            color: Theme.mutedInk
                                            font.pixelSize: Typography.metadata
                                            font.family: Typography.fontFamily
                                            elide: Text.ElideRight
                                            width: parent.width
                                        }
                                    }
                                }

                                // Action Arrow Pill
                                Rectangle {
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    height: 34
                                    width: actionLabel.implicitWidth + 24
                                    radius: 17
                                    color: Theme.surfaceActive
                                    border.color: Theme.border
                                    border.width: 1

                                    Row {
                                        anchors.centerIn: parent
                                        spacing: 4

                                        Text {
                                            id: actionLabel
                                            text: "Explore"
                                            color: Theme.deepInk
                                            font.pixelSize: Typography.caption
                                            font.bold: true
                                            font.family: Typography.fontFamily
                                        }

                                        Text {
                                            text: "→"
                                            color: Theme.subjectAccent(modelData)
                                            font.pixelSize: Typography.caption
                                            font.bold: true
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
}
