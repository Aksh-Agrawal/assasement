# Qt/QML asset path audit

Initial repository: main, clean, commit 0c2838e.

## Root cause

App.qml passes icons/home.svg as a string to PrimaryButton.iconSource. Strings carry no originating QML URL context; Image.source converts the value relative to the consuming component, producing components/icons/home.svg. Other callers guess ../icons paths, creating folder-depth coupling. No dynamic icon-name concatenation or Qt.resolvedUrl helper existed. Theme.fontFamily is system-ui; no bundled fonts or FontLoader assets are referenced. App.qml Loader source entries are QML screen routes, not icon assets, and remain relative to App.qml.

## Every original source / icon reference

```text
app/ui_qt/qml/App.qml:41: source: {
app/ui_qt/qml/App.qml:116: font.family: Theme.fontFamily
app/ui_qt/qml/App.qml:124: font.family: Theme.fontFamily
app/ui_qt/qml/App.qml:131: iconSource: "icons/home.svg"
app/ui_qt/qml/App.qml:194: font.family: Theme.fontFamily
app/ui_qt/qml/components/AppHeader.qml:28: iconSource: "../icons/arrow_back.svg"
app/ui_qt/qml/components/AppHeader.qml:48: source: "../icons/account.svg"
app/ui_qt/qml/components/AppHeader.qml:59: font.family: Theme.fontFamily
app/ui_qt/qml/components/EmptyState.qml:10: property string iconSource: "../icons/info.svg"
app/ui_qt/qml/components/EmptyState.qml:31: source: root.iconSource
app/ui_qt/qml/components/EmptyState.qml:42: font.family: Theme.fontFamily
app/ui_qt/qml/components/EmptyState.qml:50: font.family: Theme.fontFamily
app/ui_qt/qml/components/ErrorState.qml:47: font.family: Theme.fontFamily
app/ui_qt/qml/components/ErrorState.qml:58: font.family: Theme.fontFamily
app/ui_qt/qml/components/IconButton.qml:7: property string iconSource: ""
app/ui_qt/qml/components/IconButton.qml:27: source: root.iconSource
app/ui_qt/qml/components/LeaveConfirmModal.qml:39: font.family: Theme.fontFamily
app/ui_qt/qml/components/LeaveConfirmModal.qml:47: font.family: Theme.fontFamily
app/ui_qt/qml/components/LoadingState.qml:48: font.family: Theme.fontFamily
app/ui_qt/qml/components/NavRail.qml:42: source: "../icons/raspberry.svg"
app/ui_qt/qml/components/NavRail.qml:51: { id: "home", label: "Home", icon: "../icons/home.svg" },
app/ui_qt/qml/components/NavRail.qml:52: { id: "library", label: "Library", icon: "../icons/library.svg" },
app/ui_qt/qml/components/NavRail.qml:53: { id: "practice", label: "Practice", icon: "../icons/practice.svg" },
app/ui_qt/qml/components/NavRail.qml:54: { id: "history", label: "History", icon: "../icons/history.svg" },
app/ui_qt/qml/components/NavRail.qml:55: { id: "settings", label: "Settings", icon: "../icons/settings.svg" }
app/ui_qt/qml/components/NavRail.qml:81: source: modelData.icon
app/ui_qt/qml/components/NavRail.qml:91: font.family: Theme.fontFamily
app/ui_qt/qml/components/PinModal.qml:43: font.family: Theme.fontFamily
app/ui_qt/qml/components/PinModal.qml:69: font.family: Theme.fontFamily
app/ui_qt/qml/components/PinModal.qml:95: font.family: Theme.fontFamily
app/ui_qt/qml/components/PrimaryButton.qml:8: property string iconSource: ""
app/ui_qt/qml/components/PrimaryButton.qml:36: visible: root.iconSource.length > 0
app/ui_qt/qml/components/PrimaryButton.qml:37: source: root.iconSource
app/ui_qt/qml/components/PrimaryButton.qml:49: font.family: Theme.fontFamily
app/ui_qt/qml/components/QuestionOption.qml:48: font.family: Theme.fontFamily
app/ui_qt/qml/components/QuestionOption.qml:60: font.family: Theme.fontFamily
app/ui_qt/qml/components/SecondaryButton.qml:8: property string iconSource: ""
app/ui_qt/qml/components/SecondaryButton.qml:36: visible: root.iconSource.length > 0
app/ui_qt/qml/components/SecondaryButton.qml:37: source: root.iconSource
app/ui_qt/qml/components/SecondaryButton.qml:48: font.family: Theme.fontFamily
app/ui_qt/qml/components/StatusBadge.qml:80: font.family: Theme.fontFamily
app/ui_qt/qml/components/SubmitConfirmModal.qml:46: font.family: Theme.fontFamily
app/ui_qt/qml/components/SubmitConfirmModal.qml:54: font.family: Theme.fontFamily
app/ui_qt/qml/components/VirtualKeyboard.qml:59: font.family: Theme.fontFamily
app/ui_qt/qml/screens/AboutScreen.qml:46: Image { anchors.centerIn: parent; width: 36; height: 36; source: "../icons/raspberry.svg" }
app/ui_qt/qml/screens/AboutScreen.qml:55: font.family: Theme.fontFamily
app/ui_qt/qml/screens/AboutScreen.qml:63: font.family: Theme.fontFamily
app/ui_qt/qml/screens/AccountScreen.qml:49: font.family: Theme.fontFamily
app/ui_qt/qml/screens/AccountScreen.qml:66: Image { anchors.centerIn: parent; width: 22; height: 22; source: "../icons/account.svg" }
app/ui_qt/qml/screens/AccountScreen.qml:87: iconSource: "../icons/sync.svg"
app/ui_qt/qml/screens/AccountScreen.qml:126: font.family: Theme.fontFamily
app/ui_qt/qml/screens/AccountScreen.qml:167: Image { anchors.centerIn: parent; width: 18; height: 18; source: "../icons/account.svg" }
app/ui_qt/qml/screens/ChapterScreen.qml:87: font.family: Theme.fontFamily
app/ui_qt/qml/screens/ChapterScreen.qml:97: source: "../icons/chevron_right.svg"
app/ui_qt/qml/screens/ConfidenceScreen.qml:25: font.family: Theme.fontFamily
app/ui_qt/qml/screens/ConfidenceScreen.qml:33: font.family: Theme.fontFamily
app/ui_qt/qml/screens/ConfidenceScreen.qml:75: font.family: Theme.fontFamily
app/ui_qt/qml/screens/ConfidenceScreen.qml:83: font.family: Theme.fontFamily
app/ui_qt/qml/screens/ConfidenceScreen.qml:124: font.family: Theme.fontFamily
app/ui_qt/qml/screens/ConfidenceScreen.qml:132: font.family: Theme.fontFamily
app/ui_qt/qml/screens/ConfidenceScreen.qml:174: font.family: Theme.fontFamily
app/ui_qt/qml/screens/ConfidenceScreen.qml:182: font.family: Theme.fontFamily
app/ui_qt/qml/screens/ContentScreen.qml:62: Image { anchors.centerIn: parent; width: 24; height: 24; source: "../icons/download.svg" }
app/ui_qt/qml/screens/ContentScreen.qml:100: font.family: Theme.fontFamily
app/ui_qt/qml/screens/ContentScreen.qml:137: Image { anchors.centerIn: parent; width: 20; height: 20; source: "../icons/practice.svg" }
app/ui_qt/qml/screens/CreateProfileScreen.qml:43: font.family: Theme.fontFamily
app/ui_qt/qml/screens/DeviceInfoScreen.qml:46: font.family: Theme.fontFamily
app/ui_qt/qml/screens/DiagnosticsScreen.qml:57: font.family: Theme.fontFamily
app/ui_qt/qml/screens/DiagnosticsScreen.qml:76: iconSource: "../icons/diagnostics.svg"
app/ui_qt/qml/screens/DiagnosticsScreen.qml:84: iconSource: "../icons/download.svg"
app/ui_qt/qml/screens/HistoryScreen.qml:90: source: "../icons/history.svg"
app/ui_qt/qml/screens/HistoryScreen.qml:105: font.family: Theme.fontFamily
app/ui_qt/qml/screens/HistoryScreen.qml:113: font.family: Theme.fontFamily
app/ui_qt/qml/screens/HomeScreen.qml:58: font.family: Theme.fontFamily
app/ui_qt/qml/screens/HomeScreen.qml:64: font.family: Theme.fontFamily
app/ui_qt/qml/screens/HomeScreen.qml:96: source: libraryController.canResume ? "../icons/practice.svg" : "../icons/library.svg"
app/ui_qt/qml/screens/HomeScreen.qml:112: font.family: Theme.fontFamily
app/ui_qt/qml/screens/HomeScreen.qml:120: font.family: Theme.fontFamily
app/ui_qt/qml/screens/HomeScreen.qml:137: font.family: Theme.fontFamily
app/ui_qt/qml/screens/HomeScreen.qml:177: source: "../icons/library.svg"
app/ui_qt/qml/screens/HomeScreen.qml:202: source: "../icons/download.svg"
app/ui_qt/qml/screens/HomeScreen.qml:227: source: "../icons/history.svg"
app/ui_qt/qml/screens/PackScreen.qml:94: source: modelData.isInstalled ? "../icons/practice.svg" : "../icons/download.svg"
app/ui_qt/qml/screens/PackScreen.qml:111: font.family: Theme.fontFamily
app/ui_qt/qml/screens/PackScreen.qml:126: font.family: Theme.fontFamily
app/ui_qt/qml/screens/PairingScreen.qml:45: font.family: Theme.fontFamily
app/ui_qt/qml/screens/PairingScreen.qml:64: font.family: Theme.fontFamily
app/ui_qt/qml/screens/PairingScreen.qml:78: font.family: Theme.fontFamily
app/ui_qt/qml/screens/PairingScreen.qml:88: iconSource: "../icons/refresh.svg"
app/ui_qt/qml/screens/PairingScreen.qml:103: font.family: Theme.fontFamily
app/ui_qt/qml/screens/ProfilePickerScreen.qml:62: source: "../icons/account.svg"
app/ui_qt/qml/screens/ProfilePickerScreen.qml:80: source: "../icons/lock.svg"
app/ui_qt/qml/screens/ProfilePickerScreen.qml:92: font.family: Theme.fontFamily
app/ui_qt/qml/screens/ProfilePickerScreen.qml:103: font.family: Theme.fontFamily
app/ui_qt/qml/screens/ProfilePickerScreen.qml:147: source: "../icons/plus.svg"
app/ui_qt/qml/screens/ProfilePickerScreen.qml:158: font.family: Theme.fontFamily
app/ui_qt/qml/screens/QuestionDetailScreen.qml:40: font.family: Theme.fontFamily
app/ui_qt/qml/screens/QuestionNavigatorScreen.qml:46: font.family: Theme.fontFamily
app/ui_qt/qml/screens/QuestionNavigatorScreen.qml:111: font.family: Theme.fontFamily
app/ui_qt/qml/screens/QuestionScreen.qml:29: iconSource: "../icons/arrow_back.svg"
app/ui_qt/qml/screens/QuestionScreen.qml:39: font.family: Theme.fontFamily
app/ui_qt/qml/screens/QuestionScreen.qml:56: font.family: Theme.fontFamily
app/ui_qt/qml/screens/QuestionScreen.qml:84: iconSource: assessmentController.isMarkedForReview ? "../icons/flag_filled.svg" : "../icons/flag.svg"
app/ui_qt/qml/screens/QuestionScreen.qml:128: font.family: Theme.fontFamily
app/ui_qt/qml/screens/QuestionScreen.qml:183: iconSource: "../icons/library.svg"
app/ui_qt/qml/screens/RecoveryScreen.qml:43: font.family: Theme.fontFamily
app/ui_qt/qml/screens/RecoveryScreen.qml:51: font.family: Theme.fontFamily
app/ui_qt/qml/screens/ResultScreen.qml:46: font.family: Theme.fontFamily
app/ui_qt/qml/screens/ResultScreen.qml:54: font.family: Theme.fontFamily
app/ui_qt/qml/screens/ResultScreen.qml:131: iconSource: "../icons/library.svg"
app/ui_qt/qml/screens/SettingsScreen.qml:49: { id: "wifi", title: "Wi-Fi / Network", desc: "Connect to the internet and networks", icon: "../icons/wifi.svg" },
app/ui_qt/qml/screens/SettingsScreen.qml:50: { id: "sync", title: "Sync", desc: "Sync progress and assessments with cloud", icon: "../icons/sync.svg" },
app/ui_qt/qml/screens/SettingsScreen.qml:51: { id: "account", title: "Account & Profiles", desc: "Manage device pairing and study profiles", icon: "../icons/account.svg" },
app/ui_qt/qml/screens/SettingsScreen.qml:52: { id: "content", title: "Content & Downloads", desc: "Installed packs and storage space", icon: "../icons/download.svg" },
app/ui_qt/qml/screens/SettingsScreen.qml:53: { id: "software_update", title: "Software Update", desc: "System updates and version checks", icon: "../icons/update.svg" },
app/ui_qt/qml/screens/SettingsScreen.qml:54: { id: "device_info", title: "Device & System", desc: "Hardware and OS status", icon: "../icons/device.svg" },
app/ui_qt/qml/screens/SettingsScreen.qml:55: { id: "diagnostics", title: "Diagnostics", desc: "Check hardware, database and API health", icon: "../icons/diagnostics.svg" },
app/ui_qt/qml/screens/SettingsScreen.qml:56: { id: "about", title: "About", desc: "App version and device license info", icon: "../icons/info.svg" }
app/ui_qt/qml/screens/SettingsScreen.qml:87: source: modelData.icon
app/ui_qt/qml/screens/SettingsScreen.qml:102: font.family: Theme.fontFamily
app/ui_qt/qml/screens/SettingsScreen.qml:109: font.family: Theme.fontFamily
app/ui_qt/qml/screens/SettingsScreen.qml:118: source: "../icons/chevron_right.svg"
app/ui_qt/qml/screens/SoftwareUpdateScreen.qml:45: Image { anchors.centerIn: parent; width: 28; height: 28; source: "../icons/update.svg" }
app/ui_qt/qml/screens/SoftwareUpdateScreen.qml:54: font.family: Theme.fontFamily
app/ui_qt/qml/screens/SoftwareUpdateScreen.qml:82: iconSource: "../icons/refresh.svg"
app/ui_qt/qml/screens/StartupScreen.qml:29: source: "../icons/raspberry.svg"
app/ui_qt/qml/screens/StartupScreen.qml:40: font.family: Theme.fontFamily
app/ui_qt/qml/screens/StartupScreen.qml:48: font.family: Theme.fontFamily
app/ui_qt/qml/screens/StartupScreen.qml:65: font.family: Theme.fontFamily
app/ui_qt/qml/screens/SubjectScreen.qml:89: source: {
app/ui_qt/qml/screens/SubjectScreen.qml:90: if (modelData === "Mathematics") return "../icons/calculator.svg";
app/ui_qt/qml/screens/SubjectScreen.qml:91: if (modelData === "Science") return "../icons/flask.svg";
app/ui_qt/qml/screens/SubjectScreen.qml:92: return "../icons/library.svg";
app/ui_qt/qml/screens/SubjectScreen.qml:108: font.family: Theme.fontFamily
app/ui_qt/qml/screens/SubjectScreen.qml:120: font.family: Theme.fontFamily
app/ui_qt/qml/screens/SubjectScreen.qml:130: source: "../icons/chevron_right.svg"
app/ui_qt/qml/screens/SyncScreen.qml:56: source: "../icons/sync.svg"
app/ui_qt/qml/screens/SyncScreen.qml:72: font.family: Theme.fontFamily
app/ui_qt/qml/screens/SyncScreen.qml:128: iconSource: "../icons/sync.svg"
app/ui_qt/qml/screens/TestSetupScreen.qml:57: source: "../icons/practice.svg"
app/ui_qt/qml/screens/TestSetupScreen.qml:67: font.family: Theme.fontFamily
app/ui_qt/qml/screens/TestSetupScreen.qml:76: font.family: Theme.fontFamily
app/ui_qt/qml/screens/WifiScreen.qml:52: font.family: Theme.fontFamily
app/ui_qt/qml/screens/WifiScreen.qml:107: iconSource: "../icons/refresh.svg"
app/ui_qt/qml/screens/WifiScreen.qml:130: font.family: Theme.fontFamily
app/ui_qt/qml/screens/WifiScreen.qml:175: source: "../icons/wifi.svg"
app/ui_qt/qml/screens/WifiScreen.qml:206: source: "../icons/lock.svg"
app/ui_qt/qml/Theme.qml:33: readonly property string fontFamily: "system-ui"
```

## Exact icon filenames

- account.svg
- arrow_back.svg
- calculator.svg
- check.svg
- chevron_left.svg
- chevron_right.svg
- close.svg
- device.svg
- diagnostics.svg
- download.svg
- flag.svg
- flag_filled.svg
- flask.svg
- history.svg
- home.svg
- info.svg
- library.svg
- lock.svg
- plus.svg
- practice.svg
- question.svg
- raspberry.svg
- refresh.svg
- settings.svg
- star.svg
- sync.svg
- update.svg
- wifi.svg
- wifi_off.svg

## Policy

Assets.qml alone owns icon paths and resolves them against its own URL using Qt.resolvedUrl. Every caller passes Assets.<name>, including dynamic choices and JS model entries. Icon properties use url and never prepend paths. Empty optional button icons stay hidden. Required assets must exist with exact case and decode successfully in tests. No absolute machine paths, layout, colors, font or navigation changes are introduced.
