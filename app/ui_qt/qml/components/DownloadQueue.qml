import QtQuick 2.15
import QtQuick.Controls 2.15 as Controls
import QtQuick.Layouts 1.15
import ".." 1.0

Item {
    id: root

    ListView {
        id: queue
        objectName: "practiceDownloadQueue"
        anchors.fill: parent
        clip: true
        spacing: Spacing.sm
        model: libraryController.downloadQueue
        boundsBehavior: Flickable.StopAtBounds
        Controls.ScrollBar.vertical: Controls.ScrollBar { }

        delegate: AppCard {
            id: card
            required property var modelData
            readonly property bool transferring: modelData.active && modelData.state === "Downloading"
            width: queue.width - Spacing.sm
            height: details.implicitHeight + 2 * Spacing.md
            interactive: false

            RowLayout {
                id: details
                anchors.fill: parent
                anchors.margins: Spacing.md
                spacing: Spacing.md

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Spacing.xs

                    Text {
                        Layout.fillWidth: true
                        text: card.modelData.title
                        textFormat: Text.PlainText
                        font.family: Typography.family
                        font.pixelSize: Typography.body
                        font.bold: true
                        color: Theme.deepInk
                        wrapMode: Text.Wrap
                    }

                    Text {
                        Layout.fillWidth: true
                        text: {
                            switch (card.modelData.state) {
                            case "Downloading": return "Downloading " + libraryController.downloadPercent + "%";
                            case "Verifying": return "Verifying and installing…";
                            case "Preparing": return "Preparing download…";
                            case "Queued":
                                if (libraryController.libraryConnection === "offline") return "Queued · Waiting for Wi-Fi";
                                if (libraryController.libraryConnection === "auth") return "Queued · Waiting for account connection";
                                return "Queued";
                            default: return card.modelData.state;
                            }
                        }
                        font.family: Typography.family
                        font.pixelSize: Typography.caption
                        color: card.modelData.state === "Ready offline" ? Theme.forest : Theme.mutedInk
                        wrapMode: Text.Wrap
                    }

                    ProgressBar {
                        objectName: "practiceDownloadProgress"
                        visible: card.transferring
                        Layout.fillWidth: true
                        progress: libraryController.downloadPercent / 100
                        Accessible.role: Accessible.ProgressBar
                        Accessible.name: "Download progress for " + card.modelData.title
                    }
                }

                SecondaryButton {
                    visible: card.modelData.state === "Download failed"
                    text: "Retry"
                    activeFocusOnTab: true
                    Accessible.role: Accessible.Button
                    Accessible.name: "Retry " + card.modelData.title
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                    onClicked: libraryController.retryDownload(card.modelData.id, card.modelData.version)
                }
            }
        }
    }

    EmptyState {
        visible: queue.count === 0
        title: "No downloads yet"
        description: "Choose a question bank to start a download. You can queue more packs while it runs."
        actionText: "Browse question banks"
        onActionClicked: libraryController.setBrowsingBanks(true)
    }
}
