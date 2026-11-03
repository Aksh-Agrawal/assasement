import QtQuick 2.15
import ".." 1.0

Rectangle {
    id: root

    signal pauseClicked()
    signal continueClicked()

    anchors.fill: parent
    color: "#6623302D"

    MouseArea {
        anchors.fill: parent
        onClicked: root.continueClicked()
    }

    AppCard {
        anchors.centerIn: parent
        width: 480
        implicitHeight: contentCol.implicitHeight + Spacing.xl * 2

        MouseArea {
            anchors.fill: parent
        }

        Column {
            id: contentCol
            anchors.centerIn: parent
            width: parent.width - Spacing.xl * 2
            spacing: Spacing.md

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Pause Assessment?"
                color: Theme.textPrimary
                font.pixelSize: Typography.heroTitle
                font.family: Typography.fontSerif
                font.bold: true
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "All your answered questions are safely recorded. You can resume anytime from the Home screen."
                color: Theme.textSecondary
                font.pixelSize: Typography.body
                font.family: Typography.fontFamily
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
                width: parent.width
                lineHeight: 1.3
            }

            Item { width: 1; height: Spacing.xs }

            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: Spacing.md

                SecondaryButton {
                    text: "Keep Practising"
                    preferredHeight: Metrics.touchNormal
                    onClicked: root.continueClicked()
                }

                PrimaryButton {
                    text: "Pause & Exit"
                    buttonColor: Theme.forest
                    preferredHeight: Metrics.touchNormal
                    onClicked: root.pauseClicked()
                }
            }
        }
    }
}
