import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.background

    AppHeader {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        title: "Reading Passage & Detail"
        showBack: true
        onBackClicked: appController.navigate("question")
    }

    AppCard {
        anchors.top: header.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: Spacing.md

        Flickable {
            anchors.fill: parent
            anchors.margins: Spacing.lg
            contentWidth: width
            contentHeight: detailCol.implicitHeight
            clip: true

            Column {
                id: detailCol
                width: parent.width
                spacing: Spacing.md

                Row {
                    spacing: Spacing.sm
                    Rectangle {
                        width: 4
                        height: 22
                        radius: 2
                        color: Theme.forest
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        text: "Full Assessment Item Text"
                        color: Theme.textSecondary
                        font.pixelSize: Typography.caption
                        font.family: Typography.fontFamily
                        font.bold: true
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }

                Text {
                    id: detailText
                    width: parent.width
                    text: assessmentController.questionText
                    color: Theme.textPrimary
                    font.pixelSize: Typography.question
                    font.family: Typography.fontSerif
                    lineHeight: 1.45
                    wrapMode: Text.Wrap
                }
            }
        }
    }
}
