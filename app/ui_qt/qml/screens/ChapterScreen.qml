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
        title: libraryController.selectedSubject || "Chapters"
        profileText: appController.activeProfileName
        networkText: appController.networkLabel
        syncText: appController.syncLabel
        isOnline: appController.isOnline
        showBack: true
        onBackClicked: appController.navigate("subjects")
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

            model: libraryController.chapters
            visible: count > 0

            delegate: LibraryCard {
                required property string modelData
                width: grid.cellWidth - Spacing.sm
                height: grid.cardHeight
                title: modelData || "Uncategorized"
                actionText: "View packs"
                iconSource: Theme.subjectIcon(libraryController.selectedSubject)
                onClicked: libraryController.selectChapter(modelData)
            }
        }

        EmptyState {
            anchors.topMargin: 0
            visible: grid.count === 0
            title: "No chapters available"
            description: "Choose a subject with available practice questions."
            actionText: "Back to Subjects"
            onActionClicked: appController.navigate("subjects")
        }
    }
}
