import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.canvas

    NavRail {
        id: rail
        height: parent.height
        currentTab: "library"
        onTabSelected: function(tab) {
            const screens = {home: "home", library: "subjects", practice: "content",
                             progress: "progress", history: "history", settings: "settings"};
            appController.navigate(screens[tab]);
        }
    }

    AppHeader {
        id: header
        anchors.left: rail.right
        anchors.right: parent.right
        title: libraryController.selectedChapter || libraryController.selectedSubject || "Practice Packs"
        profileText: appController.activeProfileName
        networkText: appController.networkLabel
        syncText: appController.syncLabel
        isOnline: appController.isOnline
        showBack: true
        onBackClicked: appController.navigate("chapters")
    }

    Item {
        anchors.left: rail.right
        anchors.right: parent.right
        anchors.top: header.bottom
        anchors.bottom: parent.bottom
        anchors.margins: Spacing.md


        LibraryGrid {
            id: grid
            anchors.fill: parent

            model: libraryController.packs
            visible: count > 0

            delegate: LibraryPackCard {
                required property var modelData
                width: grid.cellWidth - Spacing.sm
                height: grid.cardHeight
                pack: modelData
                onClicked: {
                    if (pack.isInstalled)
                        libraryController.selectPack(pack.id, pack.version);
                    else
                        libraryController.downloadPack(pack.id, pack.version);
                }
            }
        }

        EmptyState {
            anchors.topMargin: 0
            visible: grid.count === 0
            title: "No practice packs available"
            description: "This chapter has no available practice packs."
            actionText: "Back to Chapters"
            onActionClicked: appController.navigate("chapters")
        }
    }
}
