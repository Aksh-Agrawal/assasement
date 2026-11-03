import QtQuick 2.15
import ".." 1.0

Rectangle {
    id: root

    property string text: ""
    property string statusType: "neutral" // "online", "offline", "syncing", "success", "warning", "neutral"
    property string symbol: ""

    implicitHeight: 26
    implicitWidth: badgeRow.implicitWidth + 18
    radius: Metrics.radiusPill

    color: {
        switch (statusType) {
            case "online":
            case "success": return Theme.surfaceSelected
            case "syncing": return Theme.primaryLight
            case "warning": return Theme.terracottaLight
            case "offline":
            case "error": return "#FBEAE7"
            default: return Theme.surfaceActive
        }
    }

    border.color: {
        switch (statusType) {
            case "online":
            case "success": return Theme.sage
            case "syncing": return Theme.forest
            case "warning": return Theme.terracotta
            case "offline":
            case "error": return Theme.warning
            default: return Theme.border
        }
    }
    border.width: 1

    Row {
        id: badgeRow
        anchors.centerIn: parent
        spacing: 6

        // Indicator: Vector image or crisp geometric shape
        Item {
            width: 12
            height: 12
            anchors.verticalCenter: parent.verticalCenter

            Rectangle {
                anchors.centerIn: parent
                width: 7
                height: 7
                radius: 3.5
                color: Theme.forest
                visible: root.symbol.length === 0 && (root.statusType === "online")
            }

            Rectangle {
                anchors.centerIn: parent
                width: 7
                height: 7
                radius: 3.5
                color: "transparent"
                border.color: Theme.mutedInk
                border.width: 1.5
                visible: root.symbol.length === 0 && (root.statusType === "offline")
            }

            Image {
                anchors.centerIn: parent
                width: 11
                height: 11
                source: Assets.check
                fillMode: Image.PreserveAspectFit
                visible: root.symbol.length === 0 && (root.statusType === "success")
            }

            Image {
                anchors.centerIn: parent
                width: 11
                height: 11
                source: Assets.sync
                fillMode: Image.PreserveAspectFit
                visible: root.symbol.length === 0 && (root.statusType === "syncing")
            }

            Image {
                anchors.centerIn: parent
                width: 10
                height: 10
                source: Assets.close
                fillMode: Image.PreserveAspectFit
                visible: root.symbol.length === 0 && (root.statusType === "error")
            }

            Text {
                anchors.centerIn: parent
                text: "!"
                font.bold: true
                font.pixelSize: 11
                color: Theme.terracotta
                visible: root.symbol.length === 0 && (root.statusType === "warning")
            }

            Rectangle {
                anchors.centerIn: parent
                width: 5
                height: 5
                radius: 2.5
                color: Theme.mutedInk
                visible: root.symbol.length === 0 && root.statusType === "neutral"
            }

            Text {
                anchors.centerIn: parent
                text: root.symbol
                font.pixelSize: 11
                font.bold: true
                color: Theme.mutedInk
                visible: root.symbol.length > 0
            }
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.text
            color: Theme.deepInk
            font.pixelSize: Typography.caption
            font.bold: true
            font.family: Typography.family
        }
    }
}
