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
        title: "Reading Passage / Question Detail"
        showBack: true
        onBackClicked: appController.navigate("question")
    }

    AppCard {
        anchors.top: header.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 16

        Flickable {
            anchors.fill: parent
            anchors.margins: 20
            contentWidth: width
            contentHeight: detailText.implicitHeight
            clip: true

            Text {
                id: detailText
                width: parent.width
                text: assessmentController.questionText
                color: Theme.textPrimary
                font.pixelSize: Theme.fontSizeHeading
                font.family: Theme.fontFamily
                lineHeight: 1.4
                wrapMode: Text.Wrap
            }
        }
    }
}
