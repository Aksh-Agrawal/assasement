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
        title: "Practice Library"
        profileText: appController.activeProfileName
        networkText: appController.networkLabel
        syncText: appController.syncLabel
        isOnline: appController.isOnline
        showBack: true
        onBackClicked: appController.navigate("home")
    }

    Item {
        anchors.left: rail.right
        anchors.right: parent.right
        anchors.top: header.bottom
        anchors.bottom: parent.bottom
        anchors.margins: Spacing.md

        SecondaryButton {
            id: browseButton
            text: "Browse question banks"
            onClicked: libraryController.openQuestionBanks()
        }

        LibraryGrid {
            id: grid
            anchors.fill: parent
            anchors.topMargin: browseButton.implicitHeight + Spacing.sm
            model: libraryController.subjectCards
            visible: count > 0

            delegate: LibraryCard {
                required property var modelData
                width: grid.cellWidth - Spacing.sm
                height: grid.cardHeight
                title: modelData.name
                context: modelData.chapters
                iconSource: Theme.subjectIcon(modelData.name)
                actionText: "Explore"
                onClicked: libraryController.selectSubject(modelData.name)
            }
        }

        EmptyState {
            anchors.topMargin: browseButton.implicitHeight + Spacing.sm
            visible: grid.count === 0
            title: "No practice questions downloaded yet."
            description: "Connect to Wi-Fi to browse and download question banks for offline practice."
            actionText: "Wi-Fi Settings"
            onActionClicked: appController.navigate("wifi")
        }
    }
}
