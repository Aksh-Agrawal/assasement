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
            width: parent.width - Spacing.xl * 2
            spacing: Spacing.md

            // Illustration
            Rectangle {
                width: 68
                height: 68
                radius: 34
                color: Theme.surfaceActive
                border.color: Theme.border
                border.width: 1
                anchors.horizontalCenter: parent.horizontalCenter

                Image {
                    anchors.centerIn: parent
                    width: 44
                    height: 44
                    source: Assets.recovery_guide
                    fillMode: Image.PreserveAspectFit
                }
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "We couldn't start normally"
                color: Theme.textPrimary
                font.pixelSize: Typography.heroTitle
                font.family: Typography.fontSerif
                font.bold: true
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Your learning history and saved answers are safely preserved on this device. You can restart the startup check or view system diagnostics."
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
                    text: "View Diagnostics"
                    iconSource: Assets.diagnostics
                    preferredHeight: Metrics.touchNormal
                    onClicked: appController.navigate("diagnostics")
                }

                PrimaryButton {
                    text: "Try Opening Again"
                    iconSource: Assets.refresh
                    preferredHeight: Metrics.touchNormal
                    onClicked: appController.retryStartup()
                }
            }
        }
    }
}
