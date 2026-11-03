import QtQuick 2.15
import ".." 1.0

Item {
    id: root

    property string title: "Nothing here yet"
    property string description: ""
    property string actionText: ""
    property url illustrationSource: Assets.empty_shelf
    property url iconSource: ""
    signal actionClicked()

    anchors.fill: parent

    Column {
        anchors.centerIn: parent
        spacing: Spacing.md
        width: Math.min(parent.width - 40, 480)

        Image {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 140
            height: 100
            source: root.illustrationSource
            fillMode: Image.PreserveAspectFit
            smooth: true
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.title
            color: Theme.deepInk
            font.pixelSize: Typography.sectionTitle
            font.bold: true
            font.family: Typography.family
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.description
            color: Theme.mutedInk
            font.pixelSize: Typography.body
            font.family: Typography.family
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
            width: parent.width
            visible: root.description.length > 0
        }

        Item { width: 1; height: Spacing.xs }

        PrimaryButton {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.actionText
            visible: root.actionText.length > 0
            onClicked: root.actionClicked()
        }
    }
}
