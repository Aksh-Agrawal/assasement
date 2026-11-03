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
        spacing: 5

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: {
                if (root.symbol.length > 0) return root.symbol
                switch (root.statusType) {
                    case "online": return "●"
                    case "offline": return "○"
                    case "syncing": return "↻"
                    case "success": return "✓"
                    case "warning": return "!"
                    case "error": return "✕"
                    default: return "•"
                }
            }
            font.pixelSize: 11
            color: {
                switch (root.statusType) {
                    case "online":
                    case "success": return Theme.forest
                    case "syncing": return Theme.forest
                    case "warning": return Theme.terracotta
                    case "offline":
                    case "error": return Theme.warning
                    default: return Theme.mutedInk
                }
            }
            font.bold: true
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
