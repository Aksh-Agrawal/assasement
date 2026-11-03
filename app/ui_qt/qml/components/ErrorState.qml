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
        implicitHeight: contentCol.implicitHeight + Spacing.xl * 2

        Column {
            id: contentCol
            anchors.centerIn: parent
            width: parent.width - Spacing.xl * 2
            spacing: Spacing.md

            Rectangle {
                width: 52
                height: 52
                radius: 26
                color: Theme.surfaceActive
                border.color: Theme.border
                border.width: 1
                anchors.horizontalCenter: parent.horizontalCenter

                Image {
                    anchors.centerIn: parent
                    width: 32
                    height: 32
                    source: Assets.recovery_guide
                    fillMode: Image.PreserveAspectFit
                }
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.message
                color: Theme.textPrimary
                font.pixelSize: Typography.sectionTitle
                font.family: Typography.fontSerif
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
                width: parent.width
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Your learning data is safe." + (root.errorCode.length > 0 ? " (" + root.errorCode + ")" : "")
                color: Theme.textSecondary
                font.pixelSize: Typography.metadata
                font.family: Typography.fontFamily
            }

            Item { width: 1; height: Spacing.xs }

            PrimaryButton {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.retryText
                buttonColor: Theme.forest
                preferredHeight: Metrics.touchNormal
                onClicked: root.retryClicked()
            }
        }
    }
}
