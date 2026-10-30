import QtQuick 2.15
import QtQuick.Window 2.15
import "." 1.0
import "components" 1.0
import "screens" 1.0

Window {
    id: window
    visible: true
    width: 800
    height: 480
    minimumWidth: 800
    minimumHeight: 480
    title: "Raspberry Pi Study Buddy"
    color: Theme.background

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
        anchors.fill: parent
        asynchronous: false

        source: {
            switch (appController.screen) {
                case "startup": return "screens/StartupScreen.qml";
                case "recovery": return "screens/RecoveryScreen.qml";
                case "pairing": return "screens/PairingScreen.qml";
                case "profile_picker": return "screens/ProfilePickerScreen.qml";
                case "create_profile": return "screens/CreateProfileScreen.qml";
                case "home": return "screens/HomeScreen.qml";
                case "subjects": return "screens/SubjectScreen.qml";
                case "chapters": return "screens/ChapterScreen.qml";
                case "packs": return "screens/PackScreen.qml";
                case "test_setup": return "screens/TestSetupScreen.qml";
                case "question": return "screens/QuestionScreen.qml";
                case "question_detail": return "screens/QuestionDetailScreen.qml";
                case "confidence": return "screens/ConfidenceScreen.qml";
                case "question_nav": return "screens/QuestionNavigatorScreen.qml";
                case "result": return "screens/ResultScreen.qml";
                case "review": return "screens/ReviewScreen.qml";
                case "history": return "screens/HistoryScreen.qml";
                case "settings": return "screens/SettingsScreen.qml";
                case "wifi": return "screens/WifiScreen.qml";
                case "sync": return "screens/SyncScreen.qml";
                case "account": return "screens/AccountScreen.qml";
                case "content": return "screens/ContentScreen.qml";
                case "software_update": return "screens/SoftwareUpdateScreen.qml";
                case "device_info": return "screens/DeviceInfoScreen.qml";
                case "diagnostics": return "screens/DiagnosticsScreen.qml";
                case "about": return "screens/AboutScreen.qml";
                case "institute_work": return "screens/InstituteWorkScreen.qml";
                default: return "screens/HomeScreen.qml";
            }
        }
    }

    // Global Modal Overlay: Submit Confirmation
    SubmitConfirmModal {
        id: submitConfirmModal
        visible: appController.screen === "submit_confirm"
        answeredCount: assessmentController.answeredCount
        unansweredCount: assessmentController.unansweredCount
        markedCount: assessmentController.markedCount
        onSubmitClicked: {
            assessmentController.confirmSubmit();
        }
        onReviewClicked: {
            appController.navigate("question_nav");
        }
        onCancelClicked: {
            assessmentController.cancelSubmit();
        }
    }

    // Global Toast / Message Banner
    Rectangle {
        id: toastBanner
        anchors.top: parent.top
        anchors.topMargin: appController.message.length > 0 ? 12 : -70
        anchors.horizontalCenter: parent.horizontalCenter
        width: Math.min(600, messageRow.implicitWidth + 36)
        height: 48
        radius: 24
        color: appController.notificationType === "error" ? "#FFEBEE" : (appController.notificationType === "warning" ? "#FFF3E0" : Theme.primaryLight)
        border.color: appController.notificationType === "error" ? Theme.error : (appController.notificationType === "warning" ? Theme.highlight : Theme.primary)
        border.width: 1
        visible: opacity > 0
        opacity: appController.message.length > 0 ? 1.0 : 0.0

        Behavior on anchors.topMargin {
            NumberAnimation { duration: 200; easing.type: Easing.OutQuad }
        }
        Behavior on opacity {
            NumberAnimation { duration: 200 }
        }

        Row {
            id: messageRow
            anchors.centerIn: parent
            spacing: 10

            Text {
                text: appController.notificationType === "error" ? "✕" : (appController.notificationType === "warning" ? "!" : "ℹ")
                font.pixelSize: 14
                font.bold: true
                color: appController.notificationType === "error" ? Theme.error : (appController.notificationType === "warning" ? "#C86400" : Theme.primaryDark)
            }

            Text {
                text: appController.message
                font.pixelSize: 14
                font.bold: true
                color: Theme.textPrimary
                font.family: Theme.fontFamily
            }

            MouseArea {
                width: 20
                height: 20
                anchors.verticalCenter: parent.verticalCenter
                cursorShape: Qt.PointingHandCursor
                onClicked: appController.clearMessage()
                Text { anchors.centerIn: parent; text: "✕"; font.pixelSize: 12; color: Theme.textSecondary }
            }
        }

        Timer {
            interval: 4000
            running: appController.message.length > 0
            onTriggered: appController.clearMessage()
        }
    }

    // Global Virtual Keyboard Overlay
    VirtualKeyboard {
        id: virtualKeyboard
        visible: appController.keyboardVisible
        textValue: appController.keyboardText
        isPassword: appController.keyboardIsPassword
        title: appController.keyboardTitle
        onSubmitted: function(text) {
            appController.keyboardSubmitted(text);
        }
        onCancelled: {
            appController.keyboardCancelled();
        }
    }
}
