import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.canvas

    property int selectedIndex: 0

    AppHeader {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        title: "Answer Review"
        showBack: true
        onBackClicked: appController.navigate("result")
    }

    Item {
        anchors.top: header.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: Spacing.md

        Row {
            anchors.fill: parent
            spacing: Spacing.md

            // LEFT PANEL: Question Navigation List
            AppCard {
                width: 210
                height: parent.height

                Column {
                    anchors.fill: parent
                    anchors.margins: Spacing.sm
                    spacing: Spacing.xs

                    Text {
                        text: "Questions (" + (assessmentController.reviewItems ? assessmentController.reviewItems.length : 0) + ")"
                        color: Theme.mutedInk
                        font.pixelSize: Typography.caption
                        font.bold: true
                        font.family: Typography.family
                    }

                    ListView {
                        width: parent.width
                        height: parent.height - 24
                        clip: true
                        spacing: 4
                        model: assessmentController.reviewItems

                        delegate: Rectangle {
                            width: parent.width
                            height: 44
                            radius: Metrics.radiusSmall
                            color: root.selectedIndex === index ? Theme.primaryLight : (itemMouse.containsPress ? Theme.surfaceActive : Theme.surface)
                            border.color: root.selectedIndex === index ? Theme.forest : Theme.border
                            border.width: root.selectedIndex === index ? 2 : 1

                            Item {
                                anchors.fill: parent
                                anchors.leftMargin: Spacing.sm
                                anchors.rightMargin: Spacing.sm

                                Row {
                                    anchors.left: parent.left
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 6

                                    Text {
                                        text: "Q" + modelData.index
                                        font.pixelSize: Typography.body
                                        font.bold: true
                                        color: Theme.deepInk
                                    }

                                    Image {
                                        visible: modelData.isFlagged
                                        width: 12
                                        height: 12
                                        source: Assets.flag_filled
                                        fillMode: Image.PreserveAspectFit
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                }

                                Text {
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: modelData.isCorrect ? "Correct" : "Incorrect"
                                    color: modelData.isCorrect ? Theme.forest : Theme.terracotta
                                    font.pixelSize: Typography.caption
                                    font.bold: true
                                }
                            }

                            MouseArea {
                                id: itemMouse
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.selectedIndex = index
                            }
                        }
                    }
                }
            }

            // RIGHT PANEL: Question Review Sheet
            AppCard {
                width: parent.width - 210 - Spacing.md
                height: parent.height

                Flickable {
                    anchors.fill: parent
                    anchors.margins: Spacing.md
                    contentWidth: width
                    contentHeight: reviewDetailCol.implicitHeight + Spacing.md
                    clip: true

                    readonly property var currentItem: (assessmentController.reviewItems && assessmentController.reviewItems.length > root.selectedIndex)
                        ? assessmentController.reviewItems[root.selectedIndex]
                        : null

                    Column {
                        id: reviewDetailCol
                        width: parent.width
                        spacing: Spacing.md
                        visible: parent.currentItem !== null

                        // Question index and status
                        Row {
                            width: parent.width
                            spacing: Spacing.md

                            Text {
                                text: "Question " + (parent.parent.currentItem ? parent.parent.currentItem.index : 1)
                                color: Theme.deepInk
                                font.pixelSize: Typography.sectionTitle
                                font.bold: true
                                font.family: Typography.familyEditorial
                            }

                            Rectangle {
                                height: 24
                                width: statusBadgeText.implicitWidth + 16
                                radius: 12
                                color: (parent.parent.currentItem && parent.parent.currentItem.isCorrect) ? Theme.surfaceSelected : Theme.terracottaLight
                                border.color: (parent.parent.currentItem && parent.parent.currentItem.isCorrect) ? Theme.forest : Theme.terracotta
                                border.width: 1
                                anchors.verticalCenter: parent.verticalCenter

                                Text {
                                    id: statusBadgeText
                                    anchors.centerIn: parent
                                    text: (parent.parent.parent.currentItem && parent.parent.parent.currentItem.isCorrect) ? "Correct" : "Needs Review"
                                    color: (parent.parent.parent.currentItem && parent.parent.parent.currentItem.isCorrect) ? Theme.forest : Theme.terracotta
                                    font.pixelSize: Typography.caption
                                    font.bold: true
                                }
                            }
                        }

                        // Question Prompt
                        Text {
                            width: parent.width
                            text: parent.parent.currentItem ? parent.parent.currentItem.question : ""
                            color: Theme.deepInk
                            font.pixelSize: Typography.body
                            font.bold: true
                            font.family: Typography.family
                            wrapMode: Text.Wrap
                        }

                        // Student Choice
                        Rectangle {
                            width: parent.width
                            implicitHeight: studentChoiceCol.implicitHeight + 16
                            radius: Metrics.radiusSmall
                            color: (parent.parent.currentItem && parent.parent.currentItem.isCorrect) ? Theme.surfaceSelected : Theme.terracottaLight
                            border.color: (parent.parent.currentItem && parent.parent.currentItem.isCorrect) ? Theme.forest : Theme.terracotta
                            border.width: 1

                            Column {
                                id: studentChoiceCol
                                anchors.fill: parent
                                anchors.margins: Spacing.sm
                                spacing: 2

                                Text {
                                    text: "Your Answer"
                                    color: Theme.mutedInk
                                    font.pixelSize: Typography.caption
                                    font.bold: true
                                }

                                Text {
                                    text: parent.parent.parent.parent.currentItem ? parent.parent.parent.parent.currentItem.selectedText : "Skipped"
                                    color: Theme.deepInk
                                    font.pixelSize: Typography.body
                                    font.bold: true
                                    wrapMode: Text.Wrap
                                    width: parent.width
                                }
                            }
                        }

                        // Correct Answer (if student was wrong)
                        Rectangle {
                            visible: parent.parent.currentItem && !parent.parent.currentItem.isCorrect
                            width: parent.width
                            implicitHeight: correctChoiceCol.implicitHeight + 16
                            radius: Metrics.radiusSmall
                            color: Theme.surfaceSelected
                            border.color: Theme.forest
                            border.width: 1

                            Column {
                                id: correctChoiceCol
                                anchors.fill: parent
                                anchors.margins: Spacing.sm
                                spacing: 2

                                Text {
                                    text: "Correct Answer"
                                    color: Theme.forest
                                    font.pixelSize: Typography.caption
                                    font.bold: true
                                }

                                Text {
                                    text: parent.parent.parent.parent.currentItem ? parent.parent.parent.parent.currentItem.correctText : ""
                                    color: Theme.deepInk
                                    font.pixelSize: Typography.body
                                    font.bold: true
                                    wrapMode: Text.Wrap
                                    width: parent.width
                                }
                            }
                        }

                        // Pedagogical Explanation Box
                        Rectangle {
                            visible: parent.parent.currentItem && parent.parent.currentItem.explanation.length > 0
                            width: parent.width
                            implicitHeight: explCol.implicitHeight + 16
                            radius: Metrics.radiusSmall
                            color: Theme.surfaceActive
                            border.color: Theme.border
                            border.width: 1

                            Column {
                                id: explCol
                                anchors.fill: parent
                                anchors.margins: Spacing.sm
                                spacing: 4

                                Text {
                                    text: "Explanation & Key Concept"
                                    color: Theme.deepInk
                                    font.pixelSize: Typography.caption
                                    font.bold: true
                                    font.family: Typography.family
                                }

                                Text {
                                    text: parent.parent.parent.parent.currentItem ? parent.parent.parent.parent.currentItem.explanation : ""
                                    color: Theme.deepInk
                                    font.pixelSize: Typography.body
                                    font.family: Typography.family
                                    wrapMode: Text.Wrap
                                    width: parent.width
                                    lineHeight: 1.2
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
