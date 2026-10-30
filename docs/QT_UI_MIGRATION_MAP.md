# Qt/QML UI Migration Map

This document catalogs every user-facing screen in the offline-first assessment appliance, mapping each existing Pygame implementation to its corresponding PySide6 / Qt Quick (QML) screen, underlying Python services, and migration status.

---

## 1. Migration Inventory

| Existing Screen | Current Route / State | Underlying Python Logic / Service | New Qt/QML Screen | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Startup / Boot Checks** | `UIScreen.STARTUP` / `UIScreen.SPLASH` | `app.ui.startup.StartupSession`, `app.data.repo.Repository` integrity check | `qml/screens/StartupScreen.qml` | Planned |
| **Recovery / Safety Halt** | `UIScreen.RECOVERY` | `StartupSession.failed`, local DB diagnostic, `app.data.repo.Repository.quick_check()` | `qml/screens/RecoveryScreen.qml` | Planned |
| **Device Pairing** | `UIScreen.PAIRING` | `app.ui.device.DeviceConsole` (`pair_request`, `pair_poll`), `app.api.client.DeviceApi`, `CredentialStore` | `qml/screens/PairingScreen.qml` | Planned |
| **Study Profile Picker** | `UIScreen.PROFILE` | `UIController.profiles`, `UIController.selected_profile`, `Repository.list_profiles()` | `qml/screens/ProfilePickerScreen.qml` | Planned |
| **Create Profile** | `UIScreen.ADD_PROFILE` | `UIController._activate` (`account_create`), `Repository.create_profile()` | `qml/screens/CreateProfileScreen.qml` | Planned |
| **Profile PIN Entry** | `UIScreen.PIN` | `app.auth.pin.PinUnlock`, `UIController.text_value` | `qml/components/PinModal.qml` | Planned |
| **Link Profile** | `UIScreen.LINK_PROFILE` / `UIScreen.LINK_CONFIRM` | `DeviceConsole` (`profile_claim`), `Repository.link_profile_to_account()` | `qml/components/LinkProfileModal.qml` | Planned |
| **Student Home** | `UIScreen.HOME` | `UIController.greeting`, `UIController.resume_summary`, `UIController.can_resume`, network/sync status | `qml/screens/HomeScreen.qml` | Planned |
| **Subject Selection** | `UIScreen.SUBJECTS` / `UIScreen.SUBJECT` | `UIController.subjects`, `UIController.selected_subject`, `Repository.visible_question_sets()` | `qml/screens/SubjectScreen.qml` | Planned |
| **Chapter Selection** | `UIScreen.CHAPTERS` | `UIController.chapters`, `UIController.selected_chapter` | `qml/screens/ChapterScreen.qml` | Planned |
| **Pack / Assessment Picker**| `UIScreen.PACKS` / `UIScreen.QUESTION_SET`| `UIController.subject_question_sets`, `UIController.remote_packs` | `qml/screens/PackScreen.qml` | Planned |
| **Test Setup & Instructions**| `UIScreen.TEST_SETUP` / `UIScreen.INSTRUCTIONS`| `UIController.selected_question_set`, `AssessmentApplication.start_test()`, timer/mode options | `qml/screens/TestSetupScreen.qml` | Planned |
| **Active Question** | `UIScreen.QUESTION` | `AssessmentApplication.current_question()`, `select_answer()`, `next_question()`, `previous_question()`, `AssessmentTimer` | `qml/screens/QuestionScreen.qml` | Planned |
| **Question Detail / Long Text**| `UIScreen.QUESTION_DETAIL` | `UIController.detail_page`, passage paging & scrolling | `qml/screens/QuestionDetailScreen.qml` | Planned |
| **Confidence Assessment** | `UIScreen.CONFIDENCE` | `AssessmentApplication.set_confidence()`, `Confidence.SURE / NOT_SURE / GUESSING` | `qml/screens/ConfidenceScreen.qml` | Planned |
| **Question Navigator** | `UIScreen.QUESTION_NAV` / `UIScreen.QUESTION_NAVIGATOR` | `AssessmentApplication.engine.ordered_question_ids`, `go_to_question()`, question status calculation | `qml/screens/QuestionNavigatorScreen.qml`| Planned |
| **Submit Confirmation** | `UIScreen.SUBMIT_CONFIRM` | `UIController.submit_counts`, `AssessmentApplication.submit()`, `cancel_submit()` | `qml/components/SubmitConfirmModal.qml` | Planned |
| **Leave / Pause Assessment** | `UIScreen.LEAVE_CONFIRM` / `UIScreen.ASSESSMENT_MENU` | `AssessmentApplication.pause()`, local attempt state persistence | `qml/components/LeaveConfirmModal.qml` | Planned |
| **Assessment Results** | `UIScreen.RESULT` | `UIController.result` (`ScoreResult`: score, max, percent, confidence breakdown) | `qml/screens/ResultScreen.qml` | Planned |
| **Answer Review** | `UIScreen.REVIEW` | `UIController.review_items` (`ReviewItem`: question, selected option, correct option, explanation) | `qml/screens/ReviewScreen.qml` | Planned |
| **Study History / Progress** | `UIScreen.HISTORY` / `UIScreen.PROGRESS` | `UIController.history_items`, `Repository.list_attempts()` (completed attempts, scores, sync states) | `qml/screens/HistoryScreen.qml` | Planned |
| **Settings Overview** | `UIScreen.SETTINGS` | `SETTINGS_ROUTES` category navigation | `qml/screens/SettingsScreen.qml` | Planned |
| **Wi-Fi & Network** | `UIScreen.WIFI` | `app.system.wifi.WifiService`, `DeviceConsole` (`wifi_scan`, `wifi_connect`, `wifi_forget`) | `qml/screens/WifiScreen.qml` | Planned |
| **Sync Management** | `UIScreen.SYNC` | `DeviceConsole` (`sync`), `Repository.sync_diagnostic_summary()`, pending attempts counts | `qml/screens/SyncScreen.qml` | Planned |
| **Account & Profiles** | `UIScreen.ACCOUNT` | `Repository.get_student_account_context()`, `DeviceConsole` (`account_sync`, `account_disconnect`) | `qml/screens/AccountScreen.qml` | Planned |
| **Practice & Downloads** | `UIScreen.CONTENT_UPDATES` | `DeviceConsole.catalog`, `DeviceConsole` (`download`), `Repository.list_question_sets()`, storage calculations | `qml/screens/ContentScreen.qml` | Planned |
| **Software Update** | `UIScreen.SOFTWARE_UPDATE` | `app.update.activation.ActivationManager`, `DeviceConsole` (`update_check`, `update_download`) | `qml/screens/SoftwareUpdateScreen.qml` | Planned |
| **Device & Storage Info** | `UIScreen.DEVICE_INFO` | `app.diagnostics.collect_device_status()`, `Repository.get_or_create_device_id()`, system metrics | `qml/screens/DeviceInfoScreen.qml` | Planned |
| **System Diagnostics** | `UIScreen.DIAGNOSTICS` | `app.diagnostics` (`collect_device_status`, `collect_network_status`), `Repository.quick_check()`, support bundle | `qml/screens/DiagnosticsScreen.qml` | Planned |
| **About Application** | `UIScreen.ABOUT` | App metadata, `app.version.__version__`, license & regulatory notes | `qml/screens/AboutScreen.qml` | Planned |
| **Institute Work** | `UIScreen.INSTITUTE_WORK` | `Repository.institute_work()`, `DeviceConsole` (`institute_refresh`, `institute_download`) | `qml/screens/InstituteWorkScreen.qml` | Planned |
| **On-Screen Keyboard** | Overlay in `PIN`, `ADD_PROFILE`, `LINK_PROFILE`, `WIFI` | `app.ui.screens.text_entry`, keyboard layout matrix | `qml/components/VirtualKeyboard.qml` | Planned |

---

## 2. Architecture Principles Retained
1. **Zero Database or HTTP Logic in QML**: All business rules, SQLite persistence, and HTTP calls are handled by Python controllers wrapping existing application services.
2. **Preserved Working Engine**: SQLite migrations, `AssessmentApplication`, `Repository`, `DeviceConsole`, `ActivationManager`, and `WifiService` are unchanged.
3. **Dual Execution Support**: Pygame UI remains completely intact in `app/ui/` while Qt Quick is built in `app/ui_qt/`.
4. **Touch-First 800×480 Landscape**: Designed specifically for the 5-inch 800×480 screen geometry with left navigation rail on primary screens and full-screen immersion during assessments.
