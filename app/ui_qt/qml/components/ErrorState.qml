import QtQuick 2.15
import ".." 1.0

Item {
    id: root

    property string message: "Something went wrong"
    property string errorCode: ""
    property string retryText: "Try Again"
    signal retryClicked()

    anchors.fill: parent

    AppCard {
        anchors.centerIn: parent
        width: Math.min(parent.width - 40, 460)
        implicitHeight: contentCol.implicitHeight + 40

        Column {
            id: contentCol
            anchors.centerIn: parent
            width: parent.width - 40
            spacing: 12

            Rectangle {
                width: 48
                height: 48
                radius: 24
                color: "#FFEBEE"
                anchors.horizontalCenter: parent.horizontalCenter

                Text {
                    anchors.centerIn: parent
                    text: "!"
                    color: Theme.error
                    font.pixelSize: 24
                    font.bold: true
                }
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.message
                color: Theme.textPrimary
                font.pixelSize: Theme.fontSizeHeading
                font.bold: true
                font.family: Theme.fontFamily
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
                width: parent.width
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Your data is safe." + (root.errorCode.length > 0 ? " (" + root.errorCode + ")" : "")
                color: Theme.textSecondary
                font.pixelSize: Theme.fontSizeSecondary
                font.family: Theme.fontFamily
            }

            Item { width: 1; height: 8 }

            PrimaryButton {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.retryText
                buttonColor: Theme.primary
                onClicked: root.retryClicked()
            }
        }
    }
}
