import QtQuick 2.15
import ".." 1.0

Rectangle {
    id: root

    property string text: ""
    property string statusType: "neutral" // "online", "offline", "syncing", "success", "warning", "neutral"
    property string symbol: ""

    implicitHeight: 28
    implicitWidth: badgeRow.implicitWidth + 20
    radius: Theme.pillRadius

    color: {
        switch (statusType) {
            case "online":
            case "success": return "#E8F5E9"
            case "syncing": return "#E0F2F1"
            case "warning": return "#FFF3E0"
            case "offline":
            case "error": return "#FFEBEE"
            default: return "#F5F5F5"
        }
    }

    border.color: {
        switch (statusType) {
            case "online":
            case "success": return Theme.success
            case "syncing": return Theme.primary
            case "warning": return Theme.highlight
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
            font.pixelSize: 12
            color: {
                switch (root.statusType) {
                    case "online":
                    case "success": return Theme.success
                    case "syncing": return Theme.primary
                    case "warning": return "#C86400"
                    case "offline":
                    case "error": return Theme.warning
                    default: return Theme.textSecondary
                }
            }
            font.bold: true
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.text
            color: Theme.textPrimary
            font.pixelSize: Theme.fontSizeCaption
            font.bold: true
            font.family: Theme.fontFamily
        }
    }
}
