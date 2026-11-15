import QtQuick 2.15
import QtQuick.Window 2.15
import QtQuick.Controls 2.15 as Controls
import "." 1.0
import "components" 1.0

Window {
    id: window
    visible: true
    width: 800
    height: 480
    minimumWidth: 800
    minimumHeight: 480
    title: "Questraa"
    color: Theme.paper

    Image {
        anchors.fill: parent
        source: Assets.wallpaper
        fillMode: Image.PreserveAspectCrop
        horizontalAlignment: Image.AlignLeft
        verticalAlignment: Image.AlignTop
    }

    // Keyboard navigation hooks
    Item {
        id: keyHandler
        anchors.fill: parent
        focus: true

        Keys.onEscapePressed: {
            appController.triggerAction("ACTION_BACK");
        }

        Keys.onPressed: function(event) {
            if (event.key === Qt.Key_Home) {
                appController.triggerAction("ACTION_HOME");
                event.accepted = true;
            }
        }
    }

    // Screen Router Loader
    Loader {
        id: screenLoader
        objectName: "screenLoader"
        anchors.fill: parent
        asynchronous: false
        enabled: appController.screen !== "submit_confirm"
        property string route: appController.screen

        Connections {
            target: appController
            function onScreenChanged() {
                if (appController.screen === "submit_confirm") {
                    if (screenLoader.route !== "question_nav")
                        screenLoader.route = "question";
                } else {
                    screenLoader.route = appController.screen;
                }
            }
        }

        source: {
            switch (route) {
                case "startup": return "screens/StartupScreen.qml";
                case "recovery": return "screens/RecoveryScreen.qml";
                case "pairing": return "screens/PairingScreen.qml";
                case "profile_picker": return "screens/ProfilePickerScreen.qml";
                case "create_profile": return "screens/CreateProfileScreen.qml";
                case "home": return "screens/HomeScreen.qml";
                case "library":
                case "subjects": return "screens/SubjectScreen.qml";
                case "chapters": return "screens/ChapterScreen.qml";
                case "packs": return "screens/PackScreen.qml";
                case "practice":
                case "content": return "screens/ContentScreen.qml";
                case "quick_add": return "screens/QuickAddScreen.qml";
                case "test_setup": return "screens/TestSetupScreen.qml";
                case "question": return "screens/QuestionScreen.qml";
                case "question_detail": return "screens/QuestionDetailScreen.qml";
                case "confidence": return "screens/ConfidenceScreen.qml";
                case "question_nav": return "screens/QuestionNavigatorScreen.qml";
                case "result": return "screens/ResultScreen.qml";
                case "review": return "screens/ReviewScreen.qml";
                case "progress": return "screens/ProgressScreen.qml";
                case "history": return "screens/HistoryScreen.qml";
                case "settings": return "screens/SettingsScreen.qml";
                case "wifi": return "screens/WifiScreen.qml";
                case "sync": return "screens/SyncScreen.qml";
                case "account": return "screens/AccountScreen.qml";
                case "software_update": return "screens/SoftwareUpdateScreen.qml";
                case "device_info": return "screens/DeviceInfoScreen.qml";
                case "diagnostics": return "screens/DiagnosticsScreen.qml";
                case "about": return "screens/AboutScreen.qml";
                case "institute_work": return "screens/InstituteWorkScreen.qml";
                default: return "screens/HomeScreen.qml";
            }
        }

        onStatusChanged: {
            if (status === Loader.Error) {
                console.error("[QML Loader Error] Failed to load screen for route: " + appController.screen);
            }
        }
    }

    // Error Boundary: Never show a silent blank white screen on loader error
    Rectangle {
        id: errorFallback
        anchors.fill: parent
        color: Theme.background
        visible: screenLoader.status === Loader.Error

        Column {
            anchors.centerIn: parent
            spacing: 16
            width: 480

            Rectangle {
                width: 56
                height: 56
                radius: 28
                color: "#FFEBEE"
                anchors.horizontalCenter: parent.horizontalCenter
                Text {
                    anchors.centerIn: parent
                    text: "!"
                    color: Theme.warning
                    font.pixelSize: 32
                    font.bold: true
                }
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Screen Could Not Be Loaded"
                color: Theme.textPrimary
                font.pixelSize: Theme.fontSizeHeading
                font.bold: true
                font.family: Theme.fontFamily
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "An error occurred while loading: " + appController.screen + "\nPlease return to the home screen."
                color: Theme.textSecondary
                font.pixelSize: Theme.fontSizeSecondary
                font.family: Theme.fontFamily
                horizontalAlignment: Text.AlignHCenter
            }

            PrimaryButton {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Back to Home"
                iconSource: Assets.home
                onClicked: appController.goHome()
            }
        }
    }

    // Global Modal Overlay: Submit Confirmation
    Loader {
        objectName: "submitConfirmLoader"
        anchors.fill: parent
        active: appController.screen === "submit_confirm"
        enabled: active
        focus: active
        onLoaded: (item as Item).forceActiveFocus()

        sourceComponent: SubmitConfirmModal {
            answeredCount: assessmentController.answeredCount
            unansweredCount: assessmentController.unansweredCount
            markedCount: assessmentController.markedCount
            onSubmitClicked: assessmentController.confirmSubmit()
            onReviewClicked: assessmentController.cancelSubmit(true)
            onCancelClicked: assessmentController.cancelSubmit()
        }
    }

    Controls.Popup {
        id: updateNotice
        objectName: "softwareUpdateNotice"
        anchors.centerIn: Controls.Overlay.overlay
        width: Math.min(440, window.width - Spacing.huge * 2)
        padding: Spacing.xl
        modal: true
        focus: true
        closePolicy: Controls.Popup.NoAutoClose
        visible: ["home", "subjects", "library", "chapters", "packs", "practice", "content",
                  "progress", "history", "settings"].includes(appController.screen)
                 && !appController.keyboardVisible && settingsController.updateNoticeVersion.length > 0

        background: AppCard { }

        Shortcut {
            sequences: [StandardKey.Cancel]
            enabled: updateNotice.visible
            onActivated: settingsController.dismissUpdateNotice()
        }

        contentItem: Column {
            spacing: Spacing.md

            Text {
                width: parent.width
                text: "Software update available"
                wrapMode: Text.WordWrap
                color: Theme.deepInk
                font.family: Typography.familyEditorial
                font.pixelSize: Typography.pageTitle
                font.bold: true
            }

            Text {
                width: parent.width
                text: "Version " + settingsController.updateNoticeVersion + " is available. Install it from Software Update when you're ready."
                wrapMode: Text.WordWrap
                color: Theme.mutedInk
                font.family: Typography.family
                font.pixelSize: Typography.body
            }

            Row {
                anchors.right: parent.right
                spacing: Spacing.sm

                SecondaryButton {
                    objectName: "softwareUpdateLater"
                    preferredHeight: Metrics.touchMin
                    text: "Later"
                    onClicked: settingsController.dismissUpdateNotice()
                }

                PrimaryButton {
                    objectName: "softwareUpdateView"
                    preferredHeight: Metrics.touchMin
                    text: "View update"
                    onClicked: settingsController.viewUpdateNotice()
                }
            }
        }
    }

    // Global Toast / Message Banner
    Rectangle {
        id: toastBanner
        anchors.bottom: parent.bottom
        anchors.bottomMargin: appController.message.length > 0 ? 16 : -60
        anchors.horizontalCenter: parent.horizontalCenter
        width: Math.min(600, messageText.implicitWidth + 2 * Spacing.sm + 84)
        height: Math.max(Metrics.touchMin, messageText.implicitHeight + Spacing.sm * 2)
        radius: 24
        color: appController.notificationType === "error" ? "#FFEBEE" : (appController.notificationType === "warning" ? "#FFF3E0" : Theme.primaryLight)
        border.color: appController.notificationType === "error" ? Theme.error : (appController.notificationType === "warning" ? Theme.highlight : Theme.primary)
        border.width: 1
        visible: opacity > 0
        opacity: appController.message.length > 0 ? 1.0 : 0.0

        Behavior on anchors.bottomMargin {
            NumberAnimation { duration: 200; easing.type: Easing.OutQuad }
        }
        Behavior on opacity {
            NumberAnimation { duration: 200 }
        }

        Row {
            anchors.centerIn: parent
            width: parent.width - Spacing.sm * 2
            spacing: 10

            Image {
                anchors.verticalCenter: parent.verticalCenter
                width: 16
                height: 16
                source: appController.notificationType === "error" ? Assets.close : Assets.info
                fillMode: Image.PreserveAspectFit
            }

            Text {
                id: messageText
                width: Math.max(0, parent.width - 84)
                text: appController.message
                textFormat: Text.PlainText
                wrapMode: Text.Wrap
                maximumLineCount: 3
                elide: Text.ElideRight
                anchors.verticalCenter: parent.verticalCenter
                font.pixelSize: 14
                font.bold: true
                color: Theme.textPrimary
                font.family: Theme.fontFamily
            }

            IconButton {
                width: Metrics.touchMin
                height: Metrics.touchMin
                anchors.verticalCenter: parent.verticalCenter
                text: "Dismiss notification"
                iconSource: Assets.close
                backgroundColor: "transparent"
                borderColor: "transparent"
                onClicked: appController.clearMessage()
            }
        }

        Timer {
            interval: 4000
            running: appController.message.length > 0
            onTriggered: appController.clearMessage()
        }
    }

    // Global Virtual Keyboard Overlay
    Loader {
        id: keyboardLoader
        objectName: "keyboardLoader"
        anchors.fill: parent
        active: appController.keyboardVisible
        enabled: active
        property Item previousFocus

        onLoaded: {
            previousFocus = window.activeFocusItem;
            (item as Item).forceActiveFocus();
        }
        onActiveChanged: {
            if (!active && previousFocus && previousFocus.visible) {
                previousFocus.forceActiveFocus();
                previousFocus = null;
            }
        }

        sourceComponent: VirtualKeyboard {
            textValue: appController.keyboardText
            isPassword: appController.keyboardIsPassword
            title: appController.keyboardTitle
            onSubmitted: function(text) { appController.submitKeyboard(text); }
            onCancelled: appController.keyboardCancelled()
        }
    }
}
