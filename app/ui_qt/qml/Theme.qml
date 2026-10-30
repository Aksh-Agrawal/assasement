pragma Singleton
import QtQuick 2.15

QtObject {
    id: theme

    // Palette
    readonly property color background: "#F8F4EA"
    readonly property color surface: "#FFF9F0"
    readonly property color surfaceSelected: "#EDF4EB"
    readonly property color surfaceActive: "#F3EDE2"
    readonly property color primary: "#2E7D73"
    readonly property color primaryDark: "#1E554E"
    readonly property color primaryLight: "#E0ECE8"
    readonly property color secondary: "#A7C4A0"
    readonly property color highlight: "#F4B183"
    readonly property color warning: "#D46B5B"
    readonly property color error: "#D46B5B"
    readonly property color textPrimary: "#2E2E2E"
    readonly property color textSecondary: "#5F6368"
    readonly property color textOnPrimary: "#FFFFFF"
    readonly property color success: "#3B8246"
    readonly property color divider: "#E2DCD0"
    readonly property color border: "#E2DCD0"
    readonly property color borderFocus: "#2E7D73"

    // Typography (pt sizes for clean rendering at 800x480)
    readonly property int fontSizeTitle: 26
    readonly property int fontSizeHeading: 22
    readonly property int fontSizeBody: 18
    readonly property int fontSizeSecondary: 15
    readonly property int fontSizeCaption: 14
    readonly property string fontFamily: "system-ui"

    // Dimensions & Touch Targets
    readonly property int touchMin: 48
    readonly property int touchNormal: 54
    readonly property int touchLarge: 60
    readonly property int navRailWidth: 110
    readonly property int headerHeight: 52
    readonly property int cardRadius: 14
    readonly property int buttonRadius: 12
    readonly property int pillRadius: 20

    // Animation
    readonly property int animDuration: 150
}
