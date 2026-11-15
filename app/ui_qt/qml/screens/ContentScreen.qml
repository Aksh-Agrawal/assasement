import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.canvas

    readonly property bool showingQueue: libraryController.showingDownloadQueue
    readonly property bool browsing: !showingQueue && libraryController.browsingBanks
    readonly property string bankState: libraryController.bankState
    readonly property string connectionState: libraryController.libraryConnection
    readonly property bool hasFilters: libraryController.bankFilters.some(function(value) { return value.length > 0; })
    readonly property string subjectFilter: libraryController.bankFilters[1]
    readonly property string examFilter: libraryController.bankFilters[3]
    readonly property bool filtersEnabled: !["offline", "auth"].includes(bankState)

    function applyFilters(subject, exam) {
        libraryController.filterBanks(search.text, subject, chapter.text, exam);
    }

    component LibraryButton: Button {
        id: button
        implicitHeight: Metrics.touchMin
        font.family: Typography.family
        font.pixelSize: Typography.caption
        contentItem: Text {
            text: button.text
            font: button.font
            color: button.checked ? Theme.forest : Theme.deepInk
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            opacity: button.enabled ? 1 : 0.55
        }
        background: AppCard {
            customBgColor: button.checked ? Theme.primaryLight : "transparent"
            selected: button.checked
            highlighted: button.down || button.hovered
            customBorderColor: button.activeFocus ? Theme.borderFocus : "transparent"
        }
    }

    component BankFilter: TextField {
        id: input
        required property string field
        Layout.fillWidth: true
        Layout.minimumWidth: 84
        Layout.preferredHeight: Metrics.touchMin
        font.family: Typography.family
        font.pixelSize: Typography.caption
        color: Theme.deepInk
        maximumLength: 200
        Accessible.name: placeholderText
        selectByMouse: true
        rightPadding: Metrics.touchMin

        background: AppCard {
            customBorderColor: input.activeFocus ? Theme.borderFocus : "transparent"
        }

        ToolButton {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            width: Metrics.touchMin
            height: parent.height
            icon.source: Assets.keyboard
            Accessible.name: "Open keyboard for " + input.placeholderText
            onClicked: appController.openKeyboard(input.field, input.text, false, input.placeholderText)
        }

        Connections {
            target: appController
            function onKeyboardSubmitted(value) {
                if (appController.keyboardTarget === input.field)
                    input.text = value;
            }
        }
    }

    component BankChoice: ComboBox {
        id: choice
        required property string selection
        readonly property int selectionIndex: model.findIndex(option => option.value === selection)
        Layout.preferredHeight: Metrics.touchMin
        font.family: Typography.family
        font.pixelSize: Typography.caption
        textRole: "label"
        valueRole: "value"
        currentIndex: selectionIndex
        displayText: selectionIndex >= 0 ? model[selectionIndex].label : selection
        background: AppCard {
            customBorderColor: choice.activeFocus ? Theme.borderFocus : "transparent"
            highlighted: choice.down || choice.hovered
        }
    }

    NavRail {
        id: rail
        height: parent.height
        currentTab: "practice"
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
        onBackClicked: appController.navigate("subjects")
    }

    ColumnLayout {
        anchors.left: rail.right
        anchors.right: parent.right
        anchors.top: header.bottom
        anchors.bottom: parent.bottom
        anchors.margins: Spacing.md
        spacing: Spacing.sm

        RowLayout {
            Layout.fillWidth: true
            spacing: Spacing.xs

            LibraryButton {
                text: "Downloaded"
                checked: !root.browsing && !root.showingQueue
                onClicked: libraryController.setBrowsingBanks(false)
            }

            LibraryButton {
                text: "Browse question banks"
                checked: root.browsing
                onClicked: libraryController.setBrowsingBanks(true)
            }

            LibraryButton {
                objectName: "practiceDownloadQueueTab"
                text: "Download queue" + (libraryController.pendingDownloads ? " (" + libraryController.pendingDownloads + ")" : "")
                checked: root.showingQueue
                onClicked: libraryController.openDownloadQueue()
            }

            Item { Layout.fillWidth: true }

            LibraryButton {
                visible: !root.browsing && !root.showingQueue
                text: "Quick Add"
                onClicked: {
                    quickAddController.startQuickAdd(profileController.activeProfileId);
                    appController.navigate("quick_add");
                }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: width >= 540 ? 5 : 2
            visible: root.browsing
            columnSpacing: Spacing.sm
            rowSpacing: Spacing.xs

            BankFilter {
                id: search
                field: "bank_search"
                text: libraryController.bankFilters[0]
                placeholderText: "Search question banks"
                onAccepted: apply.clicked()
            }
            BankChoice {
                id: examChoice
                objectName: "questionBankExamFilter"
                Accessible.name: "Exam"
                Layout.preferredWidth: 105
                enabled: root.filtersEnabled
                selection: root.examFilter
                model: [
                    { label: "All exams", value: "" },
                    { label: "JEE", value: "jee" },
                    { label: "IAT", value: "iat" }
                ]
                onActivated: function(index) {
                    root.applyFilters(root.subjectFilter, model[index].value);
                }
            }
            BankChoice {
                id: subjectChoice
                objectName: "questionBankSubjectFilter"
                Accessible.name: "Subject"
                Layout.preferredWidth: 132
                enabled: root.filtersEnabled
                selection: root.subjectFilter
                model: [
                    { label: "All subjects", value: "" },
                    { label: "Mathematics", value: "math" },
                    { label: "Physics", value: "Physics" },
                    { label: "Chemistry", value: "Chemistry" },
                    { label: "Biology", value: "Biology" },
                    { label: "Other subject…", value: "__custom__" }
                ]
                onActivated: function(index) {
                    const value = model[index].value;
                    if (value === "__custom__")
                        appController.openKeyboard("bank_subject", root.subjectFilter, false, "Subject");
                    else
                        root.applyFilters(value, root.examFilter);
                }

                Connections {
                    target: appController
                    function onKeyboardSubmitted(value) {
                        if (appController.keyboardTarget === "bank_subject")
                            root.applyFilters(value, root.examFilter);
                    }
                }
            }
            BankFilter {
                id: chapter
                field: "bank_chapter"
                text: libraryController.bankFilters[2]
                placeholderText: "Chapter"
                onAccepted: apply.clicked()
            }
            LibraryButton {
                id: apply
                text: "Search"
                enabled: root.filtersEnabled
                onClicked: root.applyFilters(root.subjectFilter, root.examFilter)
            }
        }

        AppCard {
            Layout.fillWidth: true
            Layout.preferredHeight: offlineCopy.implicitHeight + Spacing.md
            visible: !root.browsing && !root.showingQueue && root.connectionState === "offline" && libraryController.installedPacks.length > 0

            Text {
                id: offlineCopy
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width - 2 * Spacing.sm
                x: Spacing.sm
                text: "You're offline. Your downloaded practice questions are ready. Connect to Wi-Fi to find more."
                color: Theme.deepInk
                font.pixelSize: Typography.caption
                font.family: Typography.family
                wrapMode: Text.WordWrap
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            LibraryGrid {
                id: grid
                objectName: "questionBankGrid"
                anchors.fill: parent
                model: root.browsing ? libraryController.questionBanks : libraryController.installedPacks
                visible: !root.showingQueue && count > 0 && (!root.browsing || root.bankState === "ready")

                delegate: LibraryPackCard {
                    required property var modelData
                    width: grid.cellWidth - Spacing.sm
                    height: grid.cardHeight
                    pack: modelData
                    progressPercent: pack.status === "Downloading" ? libraryController.downloadPercent : 0
                    onClicked: {
                        if (pack.isInstalled)
                            libraryController.selectPack(pack.id, pack.version);
                        else
                            libraryController.downloadBank(pack.id, pack.version);
                    }
                }
            }

            LibraryGrid {
                id: skeleton
                anchors.fill: parent
                visible: root.browsing && ["idle", "loading"].includes(root.bankState)
                interactive: false
                Accessible.name: "Loading question banks"
                model: visible ? 4 : 0
                delegate: AppCard {
                    width: skeleton.cellWidth - Spacing.sm
                    height: skeleton.cardHeight

                    Column {
                        anchors.fill: parent
                        anchors.margins: Spacing.md
                        spacing: Spacing.sm
                        Rectangle { width: parent.width * 0.65; height: 16; radius: 4; color: Theme.borderLight }
                        Rectangle { width: parent.width * 0.36; height: 12; radius: 4; color: Theme.borderLight }
                        Text {
                            text: "Loading question banks…"
                            color: Theme.mutedInk
                            font.family: Typography.family
                            font.pixelSize: Typography.caption
                            visible: index === 0
                        }
                    }
                }
            }

            EmptyState {
                visible: !root.showingQueue && !grid.visible && !skeleton.visible
                title: {
                    if (!root.browsing)
                        return "No practice questions downloaded yet.";
                    switch (root.bankState) {
                        case "offline": return "You're offline";
                        case "auth": return "Connect this Study Profile";
                        case "unreachable": return "Question banks are unavailable";
                        default: return root.hasFilters ? "No question banks found" : "No question banks available";
                    }
                }
                description: {
                    if (!root.browsing)
                        return "Connect to Wi-Fi to browse and download question banks for offline practice.";
                    switch (root.bankState) {
                        case "offline": return "Connect to Wi-Fi to explore and download more question banks.";
                        case "auth": return "Link a Study Profile to browse and download published question banks.";
                        case "unreachable": return "The learning portal could not load the question banks. Try again in a moment.";
                        default: return root.hasFilters ? "Try a different search or clear the filters." : "Check back for published question banks.";
                    }
                }
                actionText: {
                    if (!root.browsing)
                        return root.connectionState === "offline" ? "Wi-Fi Settings" : "Browse question banks";
                    switch (root.bankState) {
                        case "offline": return "Wi-Fi Settings";
                        case "auth": return "Account settings";
                        case "unreachable": return "Try again";
                        default: return root.hasFilters ? "Clear filters" : "Refresh";
                    }
                }
                onActionClicked: {
                    if (root.browsing ? root.bankState === "offline" : root.connectionState === "offline")
                        appController.navigate("wifi");
                    else if (!root.browsing)
                        libraryController.setBrowsingBanks(true);
                    else if (root.bankState === "auth")
                        appController.navigate("account");
                    else if (root.bankState === "unreachable")
                        libraryController.refreshBanks();
                    else {
                        search.clear();
                        chapter.clear();
                        libraryController.filterBanks("", "", "", "");
                    }
                }
            }

            DownloadQueue {
                anchors.fill: parent
                visible: root.showingQueue
            }
        }

        RowLayout {
            Layout.fillWidth: true
            visible: root.browsing && root.bankState === "ready" && grid.count > 0

            LibraryButton {
                text: "Refresh"
                onClicked: libraryController.refreshBanks()
            }
            Item { Layout.fillWidth: true }
            LibraryButton {
                text: "Previous"
                visible: libraryController.hasPreviousBankPage
                onClicked: libraryController.previousBankPage()
            }
            LibraryButton {
                text: "Next"
                visible: libraryController.hasNextBankPage
                onClicked: libraryController.nextBankPage()
            }
        }
    }
}
