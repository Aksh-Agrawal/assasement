import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.background

    property int selectedIndex: 0

    AppHeader {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        title: "Review Answers"
        showBack: true
        onBackClicked: appController.navigate("result")
    }

    Item {
        anchors.top: header.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 14

        Row {
            anchors.fill: parent
            spacing: 14

            // LEFT: Question list
            AppCard {
                width: 220
                height: parent.height

                Column {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8

                    Text {
                        text: "Questions"
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontSizeCaption
                        font.bold: true
                    }

                    ListView {
                        width: parent.width
                        height: parent.height - 40
                        clip: true
                        spacing: 6
                        model: assessmentController.reviewItems

                        delegate: Rectangle {
                            width: parent.width
                            height: 44
                            radius: 8
                            color: root.selectedIndex === index ? Theme.primaryLight : (itemMouse.containsPress ? Theme.surfaceActive : Theme.surface)
                            border.color: root.selectedIndex === index ? Theme.primary : Theme.border
                            border.width: root.selectedIndex === index ? 2 : 1

                            Item {
                                anchors.fill: parent
                                anchors.leftMargin: 10
                                anchors.rightMargin: 10

                                Text {
                                    anchors.left: parent.left
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "Q" + modelData.index
                                    font.pixelSize: 14
                                    font.bold: true
                                    color: Theme.textPrimary
                                }

                                Text {
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: modelData.isCorrect ? "✓ Correct" : "✕ Incorrect"
                                    color: modelData.isCorrect ? Theme.success : Theme.warning
                                    font.pixelSize: 12
                                    font.bold: true
                                }
                            }

                            MouseArea {
                                id: itemMouse
                                anchors.fill: parent
                                onClicked: root.selectedIndex = index
                            }
                        }
                    }
                }
            }

            // RIGHT: Selected Question Review Details
            AppCard {
                width: parent.width - 220 - 14
                height: parent.height

                Item {
                    anchors.fill: parent
                    anchors.margins: 16

                    readonly property var currentItem: (assessmentController.reviewItems && assessmentController.reviewItems.length > root.selectedIndex)
                        ? assessmentController.reviewItems[root.selectedIndex]
                        : null

                    Column {
                        anchors.fill: parent
                        spacing: 10
                        visible: parent.currentItem !== null

                        Row {
                            spacing: 8
                            Text {
                                text: "Question " + (parent.parent.currentItem ? parent.parent.currentItem.index : 1)
                                color: Theme.textPrimary
                                font.pixelSize: Theme.fontSizeHeading
                                font.bold: true
                            }

                            StatusBadge {
                                text: (parent.parent.currentItem && parent.parent.currentItem.isCorrect) ? "Correct ✓" : "Needs Review"
                                statusType: (parent.parent.currentItem && parent.parent.currentItem.isCorrect) ? "success" : "warning"
                            }
                        }

                        // Question text
                        Flickable {
                            width: parent.width
                            height: Math.min(80, qText.implicitHeight)
                            contentWidth: width
                            contentHeight: qText.implicitHeight
                            clip: true

                            Text {
                                id: qText
                                width: parent.width
                                text: parent.parent.parent.currentItem ? parent.parent.parent.currentItem.question : ""
                                color: Theme.textPrimary
                                font.pixelSize: Theme.fontSizeBody
                                wrapMode: Text.Wrap
                            }
                        }

                        // Student Choice vs Correct Choice
                        Column {
                            width: parent.width
                            spacing: 6

                            Rectangle {
                                width: parent.width
                                height: 42
                                radius: 8
                                color: (parent.parent.parent.currentItem && parent.parent.parent.currentItem.isCorrect) ? "#E8F5E9" : "#FFEBEE"
                                border.color: (parent.parent.parent.currentItem && parent.parent.parent.currentItem.isCorrect) ? Theme.success : Theme.warning

                                Row {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 8
                                    Text { text: "Your answer:"; font.bold: true; color: Theme.textPrimary; font.pixelSize: 13 }
                                    Text {
                                        text: parent.parent.parent.parent.currentItem ? parent.parent.parent.parent.currentItem.selectedText : ""
                                        color: Theme.textPrimary
                                        font.pixelSize: 13
                                    }
                                }
                            }

                            Rectangle {
                                width: parent.width
                                height: 42
                                radius: 8
                                color: "#E8F5E9"
                                border.color: Theme.success
                                visible: parent.parent.parent.currentItem && !parent.parent.parent.currentItem.isCorrect

                                Row {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 8
                                    Text { text: "Correct answer:"; font.bold: true; color: Theme.success; font.pixelSize: 13 }
                                    Text {
                                        text: parent.parent.parent.parent.currentItem ? parent.parent.parent.parent.currentItem.correctText : ""
                                        color: Theme.textPrimary
                                        font.pixelSize: 13
                                    }
                                }
                            }
                        }

                        // Explanation
                        Text {
                            text: parent.parent.currentItem && parent.parent.currentItem.explanation.length > 0
                                ? "Explanation: " + parent.parent.currentItem.explanation
                                : "No additional explanation for this question."
                            color: Theme.textSecondary
                            font.pixelSize: Theme.fontSizeCaption
                            wrapMode: Text.Wrap
                            width: parent.width
                        }

                        Item { width: 1; height: 10 }

                        // Bottom navigation between items
                        Row {
                            anchors.right: parent.right
                            spacing: 10

                            SecondaryButton {
                                text: "← Prev"
                                preferredHeight: 44
                                enabled: root.selectedIndex > 0
                                onClicked: root.selectedIndex--
                            }

                            SecondaryButton {
                                text: "Next →"
                                preferredHeight: 44
                                enabled: root.selectedIndex < assessmentController.reviewItems.length - 1
                                onClicked: root.selectedIndex++
                            }

                            PrimaryButton {
                                text: "Done"
                                preferredHeight: 44
                                onClicked: appController.navigate("home")
                            }
                        }
                    }
                }
            }
        }
    }
}
