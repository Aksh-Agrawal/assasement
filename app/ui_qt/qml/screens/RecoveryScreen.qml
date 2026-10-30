import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.background

    AppCard {
        anchors.centerIn: parent
        width: 520
        implicitHeight: contentCol.implicitHeight + 48

        Column {
            id: contentCol
            anchors.centerIn: parent
            width: parent.width - 48
            spacing: 16

            Rectangle {
                width: 60
                height: 60
                radius: 30
                color: "#FFEBEE"
                anchors.horizontalCenter: parent.horizontalCenter

                Text {
                    anchors.centerIn: parent
                    text: "!"
                    color: Theme.warning
                    font.pixelSize: 32
                    font.bold: true
                }
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "We couldn't start normally."
                color: Theme.textPrimary
                font.pixelSize: Theme.fontSizeTitle
                font.bold: true
                font.family: Theme.fontFamily
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Your assessment data is safe. Try restarting the check or run diagnostics."
                color: Theme.textSecondary
                font.pixelSize: Theme.fontSizeBody
                font.family: Theme.fontFamily
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
                width: parent.width
            }

            Item { width: 1; height: 8 }

            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 16

                SecondaryButton {
                    text: "Diagnostics"
                    preferredHeight: Theme.touchNormal
                    onClicked: appController.navigate("diagnostics")
                }

                PrimaryButton {
                    text: "Try Again"
                    preferredHeight: Theme.touchNormal
                    onClicked: appController.retryStartup()
                }
            }
        }
    }
}
