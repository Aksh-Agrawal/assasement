import QtQuick 2.15
import ".." 1.0

Rectangle {
    id: root

    signal pauseClicked()
    signal continueClicked()

    anchors.fill: parent
    color: "#802E2E2E"

    MouseArea {
        anchors.fill: parent
        onClicked: root.continueClicked()
    }

    AppCard {
        anchors.centerIn: parent
        width: 480
        implicitHeight: contentCol.implicitHeight + 44

        MouseArea {
            anchors.fill: parent
        }

        Column {
            id: contentCol
            anchors.centerIn: parent
            width: parent.width - 44
            spacing: 14

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Pause Assessment?"
                color: Theme.textPrimary
                font.pixelSize: Theme.fontSizeTitle
                font.bold: true
                font.family: Theme.fontFamily
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Your answers are saved. You can continue anytime from the Home screen."
                color: Theme.textSecondary
                font.pixelSize: Theme.fontSizeBody
                font.family: Theme.fontFamily
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
                width: parent.width
            }

            Item { width: 1; height: 6 }

            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 16

                SecondaryButton {
                    text: "Keep Practising"
                    preferredHeight: Theme.touchNormal
                    onClicked: root.continueClicked()
                }

                PrimaryButton {
                    text: "Pause & Exit"
                    buttonColor: Theme.primary
                    preferredHeight: Theme.touchNormal
                    onClicked: root.pauseClicked()
                }
            }
        }
    }
}
