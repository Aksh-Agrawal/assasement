import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.background

    Row {
        anchors.fill: parent

        NavRail {
            id: rail
            height: parent.height
            currentTab: "home"
            onTabSelected: function(tab) {
                if (tab === "home") appController.navigate("home");
                else if (tab === "library") appController.navigate("subjects");
                else if (tab === "practice") appController.navigate("content");
                else if (tab === "progress") appController.navigate("progress");
                else if (tab === "history") appController.navigate("history");
                else if (tab === "settings") appController.navigate("settings");
            }
        }

        Column {
            width: parent.width - rail.width
            height: parent.height

            AppHeader {
                width: parent.width
                title: "Institute Work & Homework"
                profileText: appController.activeProfileName
                networkText: appController.networkLabel
                syncText: appController.syncLabel
                isOnline: appController.isOnline
                showBack: true
                onBackClicked: appController.navigate("home")
            }

            Item {
                width: parent.width
                height: parent.height - Metrics.headerHeight

                EmptyState {
                    anchors.centerIn: parent
                    title: "No Assigned Homework"
                    description: "When your school, tutor, or learning center assigns practice packs, they will appear in this folder."
                    actionText: "Explore Practice Library"
                    onActionClicked: appController.navigate("subjects")
                }
            }
        }
    }
}
