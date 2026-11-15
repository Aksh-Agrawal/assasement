import QtQuick 2.15
import QtQuick.Controls 2.15
import ".." 1.0

GridView {
    id: grid
    property int columns: width >= 500 ? 2 : 1
    property int cardHeight: 115
    cellWidth: Math.floor(width / columns)
    cellHeight: cardHeight + Spacing.sm
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    keyNavigationEnabled: true
    ScrollBar.vertical: ScrollBar {
        policy: grid.interactive ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
    }
}
