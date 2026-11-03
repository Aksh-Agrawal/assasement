pragma Singleton
import QtQuick 2.15

QtObject {
    id: metrics

    // Touch targets (WCAG 2.2 AA baseline: >= 48px)
    readonly property int touchMin: 48
    readonly property int touchNormal: 54
    readonly property int touchLarge: 60

    // Corner Radii
    readonly property int radiusSmall: 6
    readonly property int radiusSm: 6
    readonly property int radiusMedium: 10
    readonly property int radiusMd: 10
    readonly property int radiusLarge: 14
    readonly property int radiusLg: 14
    readonly property int radiusPill: 24

    // Structural Dimensions
    readonly property int navRailWidth: 96
    readonly property int headerHeight: 46
    readonly property int borderThin: 1
    readonly property int borderFocus: 2

    // Shadows / Elevations
    readonly property int elevationLight: 2
}
