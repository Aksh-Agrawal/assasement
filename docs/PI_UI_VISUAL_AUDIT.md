# Raspberry Pi UI Visual & Architecture Audit

## 1. Executive Summary & Hardware Context

This audit evaluates the Qt Quick / QML interface in `app/ui_qt/` for the Raspberry Pi Zero 2 W assessment device.

### Target Hardware Constraints
- **Device**: Raspberry Pi Zero 2 W
- **Memory**: 512 MB LPDDR2 RAM (shared with VideoCore IV GPU)
- **Display**: 5-inch DSI/HDMI touchscreen, 800 × 480 native resolution (landscape, 5:3 aspect ratio)
- **Input**: Capacitive single/multi-touch, hardware power/home buttons, optional USB keyboard
- **Graphics Pipeline**: Linux DRM/KMS / eglfs with basic Qt Quick scene graph (`QSG_RENDER_LOOP=basic`), software/GLES rasterization

### Critical Findings
The existing Qt Quick UI is functionally solid: the controllers (`AppController`, `ProfileController`, `LibraryController`, `AssessmentController`, `SettingsController`) interface cleanly with the underlying SQLite database, assessment engine, credential store, and background sync worker.
However, visually the current UI suffers from the classic "generic Qt / AI template" syndrome:
1. **Plain background + rounded white boxes + generic teal buttons**: Every screen relies on the exact same `AppCard` (white card with 14px radius and 1px border) placed over a plain beige background (`#F8F4EA`).
2. **Lack of Graphical Personality**: There are zero educational illustrations, diagrams, botanical motifs, or subject markers. The only graphics are 29 generic SVG stroke icons (standard Feather/Lucide icons) rendered inside small colored circles.
3. **Weak Visual Hierarchy**: Typography hierarchy is compressed, with bold applied excessively to labels, headings, and buttons without editorial nuance.
4. **Card Overuse & Inappropriate Patterns**: Screens that should be flat appliance lists (Settings, Wi-Fi) wrap every row in an individual `AppCard`. The Home screen displays four cards of equal weight without a clear primary educational hero.
5. **Missing Paper / Book Tactility**: The interface lacks the warm, printed-book, tactile educational atmosphere required by the product vision.

---

## 2. Existing Design Tokens & Assets Audit

### 2.1 Theme.qml Tokens
- **Current Background**: `#F8F4EA` (Eggshell)
- **Current Surface**: `#FFF9F0` (Warm Off-White)
- **Current Accent**: `#2E7D73` (Teal) / `#1E554E` (Forest Teal)
- **Typography**: `fontFamily: "system-ui"` (Failed Qt offscreen font engine, required explicit system font matching)
- **Sizes**: Title 26px, Heading 22px, Body 18px, Secondary 15px, Caption 14px
- **Problems**:
  - Missing distinct subject identities (Biology, Chemistry, Mathematics, Literature).
  - Lacks dedicated palette tokens for paper-cut layers, book motifs, deep ink, muted ink, terracotta, warm gold, and soft sky.
  - Spacing and metrics are scattered with ad-hoc margins across screens rather than governed by dedicated `Spacing.qml` and `Metrics.qml`.

### 2.2 Assets.qml & Icon System
- **Current Structure**: Flat list of 29 SVG stroke icons in `app/ui_qt/qml/icons/`.
- **Problems**:
  - No illustration directories (`illustrations/`, `subjects/`, `decorative/`).
  - No subject-specific visual assets (leaf/cell/DNA for Biology, flask/molecule for Chemistry, compass/geometry for Math, open book/telescope for General Science).
  - Icons are monochrome line drawings inside circular badges, looking like an admin dashboard.

---

## 3. Screen-by-Screen Detailed Audit

### 3.1 StartupScreen (`screens/StartupScreen.qml`)
- **Current Purpose**: Displays system startup, performs diagnostic integrity checks, and loads initial state.
- **Business Logic Dependencies**: `appController.startupProgress`, `appController.startupStatus`.
- **Component Dependencies**: `Theme.qml`, `ProgressBar.qml`, `Assets.qml`.
- **Visual Problems**:
  - Single centered column with a tiny raspberry icon inside a circle, text, and a generic progress bar.
  - Feels like a generic device booting up rather than opening a thoughtful educational book or learning companion.
- **Planned New Treatment**:
  - Warm paper canvas with tactile vignette and an illustrated learning emblem (open book + star of knowledge / botanical flourish).
  - Elegant serif/slab editorial typography: "Preparing your study space".
  - Refined two-tone progress indicator with smooth ease and subtle ink status label.

### 3.2 RecoveryScreen (`screens/RecoveryScreen.qml`)
- **Current Purpose**: Displays actionable recovery options when database verification or boot check fails.
- **Business Logic Dependencies**: `appController.recoveryMessage`, `appController.retryStartup()`, `appController.openDiagnostics()`.
- **Component Dependencies**: `Theme.qml`, `AppCard.qml`, `PrimaryButton.qml`, `SecondaryButton.qml`.
- **Visual Problems**:
  - Warning triangle icon in a pink circle inside a standard white card. Looks alarming and technical.
- **Planned New Treatment**:
  - Calm, reassuring educational tone: "We ran into a bump opening your library."
  - Tactile rescue graphic (calm lantern / notebook illustration).
  - Clear, accessible primary recovery button ("Try Opening Again") and secondary ("View Health Checks").

### 3.3 PairingScreen (`screens/PairingScreen.qml`)
- **Current Purpose**: Shows 6-character device pairing code for student-cloud account connection.
- **Business Logic Dependencies**: `settingsController.pairingCode`, `settingsController.pairingTimeRemaining`, `settingsController.isPairing`.
- **Component Dependencies**: `Theme.qml`, `AppHeader.qml`, `AppCard.qml`, `PrimaryButton.qml`.
- **Visual Problems**:
  - Giant card with monospace characters in a grey box, surrounded by bulleted text.
- **Planned New Treatment**:
  - Two-column layout: Left column features an illustrated connection scene (Raspberry Pi device communicating with cloud book); Right column presents the 6-character code styled like a printed physical stamp/ticket with generous letter spacing, remaining time chip, and clear step-by-step guidance.

### 3.4 ProfilePickerScreen (`screens/ProfilePickerScreen.qml`)
- **Current Purpose**: Allows student selection ("Who's studying today?") and navigation to Add Profile.
- **Business Logic Dependencies**: `profileController.profiles`, `profileController.selectProfileId()`, `profileController.switchMode`, `profileController.cancelSwitch()`.
- **Component Dependencies**: `Theme.qml`, `AppHeader.qml`, `AppCard.qml`, `SecondaryButton.qml`.
- **Visual Problems**:
  - Three identical vertical cards with standard generic user silhouette icons inside grey circles.
  - Feels like an OS account picker or multi-tenant login screen.
- **Planned New Treatment**:
  - Learner identity cards with custom character/subject avatar illustrations, student name in strong warm ink typography, exam target badge (NEET, JEE, Class 10), and tactile embossed card treatment.
  - Dotted-outline "+ Add Learner" card styled like an open notebook invitation.

### 3.5 CreateProfileScreen (`screens/CreateProfileScreen.qml`)
- **Current Purpose**: Form to create a new local study profile with name and exam goal.
- **Business Logic Dependencies**: `profileController.createProfile()`, `appController.openKeyboard()`.
- **Component Dependencies**: `Theme.qml`, `AppHeader.qml`, `AppCard.qml`, `PrimaryButton.qml`.
- **Visual Problems**:
  - Generic form inputs with standard text boxes.
- **Planned New Treatment**:
  - Notebook-inspired creation sheet with tactile input fields, avatar selection chips with illustrated animals/motifs, and clear focus-visible borders.

### 3.6 HomeScreen (`screens/HomeScreen.qml`)
- **Current Purpose**: Primary landing dashboard answering: Who am I? What should I do next? What did I do recently?
- **Business Logic Dependencies**: `appController.activeProfileName`, `libraryController.canResume`, `libraryController.resumeTitle`, `libraryController.resumeAnswered`, `libraryController.resumeTotal`, `assessmentController.resumeTest()`.
- **Component Dependencies**: `NavRail.qml`, `AppHeader.qml`, `AppCard.qml`, `ProgressBar.qml`, `PrimaryButton.qml`.
- **Visual Problems**:
  - "Four equal cards" layout: One big card on top + 3 identical cards on bottom with icons floating over card borders.
  - Plain background, generic teal button. Zero graphical storytelling.
- **Planned New Treatment**:
  - Illustration-led educational hero: Integrates a rich, lightweight vector scene (open study desk, books, telescope, botanical accent) alongside a warm greeting: "Good morning, Aksh — Ready for today's practice?".
  - Contextual Hero state:
    - If in-progress test: "Continue Biology • Cell Structure — 6 of 10 complete" with tactile progress rail and strong "Continue Practice" CTA.
    - If clean state: "Ready for something new? Choose a subject and start practicing" with strong "Browse Practice" CTA.
  - Compact tactile secondary destinations: Illustrated subject quick-hops (Biology, Chemistry, Mathematics) with custom subject artwork.

### 3.7 SubjectScreen (`screens/SubjectScreen.qml`)
- **Current Purpose**: Subject catalog for selecting Biology, Chemistry, Mathematics, English, etc.
- **Business Logic Dependencies**: `libraryController.subjects`, `libraryController.selectSubject()`.
- **Component Dependencies**: `NavRail.qml`, `AppHeader.qml`, `AppCard.qml`, `EmptyState.qml`.
- **Visual Problems**:
  - 2x2 grid of generic rounded rectangles with simple calculator/flask stroke icons.
- **Planned New Treatment**:
  - "Practice Library" bookshelf / editorial subject cards:
    - Biology: Forest teal & sage palette with botanical leaf/DNA vector illustration, chapter count, and topic preview ("Cells • Genetics • Physiology").
    - Chemistry: Warm terracotta & apricot palette with molecular flask/atom artwork and topic preview ("Atoms • Bonding • Reactions").
    - Mathematics: Deep ink & warm gold palette with geometric compass/graph illustration and topic preview ("Numbers • Algebra • Geometry").
    - General Science / English: Soft sky palette with open book/telescope artwork.

### 3.8 ChapterScreen (`screens/ChapterScreen.qml`)
- **Current Purpose**: Lists chapters/topics within a selected subject.
- **Business Logic Dependencies**: `libraryController.selectedSubject`, `libraryController.chapters`, `libraryController.selectChapter()`.
- **Component Dependencies**: `NavRail.qml`, `AppHeader.qml`, `AppCard.qml`, `EmptyState.qml`.
- **Visual Problems**:
  - Full-width list where every chapter is a separate floating white card with a chevron icon.
- **Planned New Treatment**:
  - Cohesive subject-branded chapter ledger:
    - Subject banner header featuring the subject motif (e.g. subtle sage foliage for Biology).
    - Clean, tactile chapter rows separated by subtle ink dividers rather than individual floating cards.
    - Topic item count marker and progress indicators ("3 sets available >").

### 3.9 PackScreen (`screens/PackScreen.qml`)
- **Current Purpose**: Lists specific question sets / assessment packs within a chapter.
- **Business Logic Dependencies**: `libraryController.packs`, `libraryController.selectPack()`, `libraryController.downloadPack()`.
- **Component Dependencies**: `NavRail.qml`, `AppHeader.qml`, `AppCard.qml`, `PrimaryButton.qml`, `StatusBadge.qml`.
- **Visual Problems**:
  - Generic card list with multiple badges, small icons, and action buttons. Exposes technical pack details.
- **Planned New Treatment**:
  - Educational study booklets:
    - Clean title ("Cell Biology Basics"), question count ("10 questions • ~8 mins"), offline status ("Ready offline").
    - Prominent tactile "Start Practice" or "Download to Pi" action.
    - Subject-accented left spine indicator.

### 3.10 TestSetupScreen (`screens/TestSetupScreen.qml`)
- **Current Purpose**: Pre-test configuration: timer selection, practice mode selection, start button.
- **Business Logic Dependencies**: `assessmentController.startTest()`, `libraryController.selectedPack`.
- **Component Dependencies**: `AppCard.qml`, `PrimaryButton.qml`, `SecondaryButton.qml`.
- **Visual Problems**:
  - Left card with metadata; right card with multiple button grids. Incoherent proportions.
- **Planned New Treatment**:
  - Clean pre-flight briefing card:
    - Illustrated subject badge and set overview.
    - Clear segmented selectors for Timer ("No timer", "10 min", "20 min") and Mode ("Practice with hints", "Timed Test").
    - Large, prominent primary CTA: "Begin Assessment →" (54px touch target).

### 3.11 QuestionScreen (`screens/QuestionScreen.qml`)
- **Current Purpose**: The primary assessment execution view. Renders question, options, timer, flag, navigation.
- **Business Logic Dependencies**: `assessmentController.questionText`, `assessmentController.options`, `assessmentController.selectAnswer()`, `assessmentController.nextQuestion()`, `assessmentController.previousQuestion()`, `assessmentController.toggleMarkReview()`, `assessmentController.requestSubmit()`.
- **Component Dependencies**: `QuestionOption.qml`, `IconButton.qml`, `PrimaryButton.qml`, `SecondaryButton.qml`, `LeaveConfirmModal.qml`.
- **Visual Problems**:
  - Top header has cramped text and floating toasts that occlude the header.
  - 2x2 option grid truncates long answer options and breaks on multi-line text.
  - Bottom bar is tall (64px) and eats vertical space from the 480px total height.
  - Zero subject personality.
- **Planned New Treatment**:
  - Academically focused, high-contrast, distraction-free 800×480 layout:
    - Header (42px compact): Subject · Chapter breadcrumb, slim progress rail, discreet timer badge, bookmark/flag toggle.
    - Question Area: Prominent question text in deep ink (`#23302D`, 21px bold), flickable for long multi-line paragraphs, with optional diagram/graphic support.
    - Answer Options: Tactile vertical stack or resilient 2-column adaptive layout with minimum 52px height, full text wrapping, clear letter discs (A, B, C, D), and tactile selected state (sage/teal tint with check marker).
    - Bottom Navigation (50px compact): Left: "Mark for Review" + "Overview Grid"; Right: "← Prev" + "Next Question →" / "Submit Test".

### 3.12 QuestionDetailScreen (`screens/QuestionDetailScreen.qml`)
- **Current Purpose**: Full-screen modal for reading long reading passages or inspecting diagrams.
- **Business Logic Dependencies**: `assessmentController.questionText`, `assessmentController.diagramUrl`.
- **Component Dependencies**: `Theme.qml`, `AppCard.qml`, `PrimaryButton.qml`.
- **Visual Problems**:
  - Plain white box covering the screen.
- **Planned New Treatment**:
  - Editorial reading sheet with parchment texture, legible serif/sans typography, zoomable diagram viewport, and clear "Return to Question" header.

### 3.13 ConfidenceScreen (`screens/ConfidenceScreen.qml`)
- **Current Purpose**: Post-answer metacognitive self-assessment ("How confident are you?").
- **Business Logic Dependencies**: `assessmentController.setConfidence("sure" | "not_sure" | "guessing" | "unrated")`.
- **Component Dependencies**: `Theme.qml`, `AppCard.qml`, `SecondaryButton.qml`.
- **Visual Problems**:
  - Three identical cards with star, dot, and question mark icons.
- **Planned New Treatment**:
  - Tactile tri-choice cards with expressive custom symbols:
    - "Sure": Bullseye / solid star icon in soft sage ("I knew the answer").
    - "Not sure": Balanced scales / dual-path icon in warm gold ("I narrowed it down").
    - "Guessing": Die / exploratory compass in soft terracotta ("I took a guess").
  - Clear tactile touch targets (180px height, 190px width) with instant responsive feedback.

### 3.14 QuestionNavigatorScreen (`screens/QuestionNavigatorScreen.qml`)
- **Current Purpose**: 2D question grid overview for jumping between questions and reviewing status.
- **Business Logic Dependencies**: `assessmentController.navigatorQuestions`, `assessmentController.jumpToQuestion()`.
- **Component Dependencies**: `Theme.qml`, `AppHeader.qml`, `AppCard.qml`, `PrimaryButton.qml`.
- **Visual Problems**:
  - Generic number buttons in a cramped grid; unclear legend.
- **Planned New Treatment**:
  - Organized test map:
    - Summary ledger on left: Total Answered (sage), Unanswered (parchment), Flagged (gold banner).
    - Grid of tactile numbered tiles (minimum 48×48px) with accessible shape + color encoding (pill for current, check for answered, flag for review).

### 3.15 ResultScreen (`screens/ResultScreen.qml`)
- **Current Purpose**: Displays assessment completion score, percentage, and confidence analytics.
- **Business Logic Dependencies**: `assessmentController.score`, `assessmentController.scoreMax`, `assessmentController.scorePercent`, `assessmentController.confidenceBreakdown`, `assessmentController.openReview()`, `assessmentController.finishAndGoHome()`.
- **Component Dependencies**: `Theme.qml`, `AppCard.qml`, `PrimaryButton.qml`, `SecondaryButton.qml`.
- **Visual Problems**:
  - Uses party popper emoji "🎉", generic score pill, and dashboard-style dividers.
- **Planned New Treatment**:
  - Restrained, proud academic achievement celebration:
    - Warm engraved laurel or achievement emblem illustration.
    - Bold hero score: "8 / 10" with "80% Mastery".
    - Clean summary chips: "8 Correct", "2 Incorrect".
    - Refined confidence correlation bar.
    - Primary CTA: "Review Answers" (Forest Teal); Secondary: "Finish Practice" (Warm Parchment).

### 3.16 ReviewScreen (`screens/ReviewScreen.qml`)
- **Current Purpose**: Detailed answer key review showing questions, selected vs correct answers, and explanations.
- **Business Logic Dependencies**: `assessmentController.reviewItems`, `assessmentController.openReview()`.
- **Component Dependencies**: `Theme.qml`, `AppHeader.qml`, `AppCard.qml`, `StatusBadge.qml`.
- **Visual Problems**:
  - Split view with heavy bordered cards; explanation text is cramped.
- **Planned New Treatment**:
  - Calm academic study journal:
    - Left column: Clean question index strip showing status glyphs (✓ / ✗ / 🚩).
    - Right area: Editorial review card showing question text, student's response highlighted, correct answer with clear check badge, and pedagogical explanation card on soft sage surface.

### 3.17 HistoryScreen (`screens/HistoryScreen.qml`)
- **Current Purpose**: Student's past assessment log and scores.
- **Business Logic Dependencies**: `assessmentController.historyList`.
- **Component Dependencies**: `NavRail.qml`, `AppHeader.qml`, `AppCard.qml`, `EmptyState.qml`.
- **Visual Problems**:
  - List of floating white cards with small clock icons and colored score pills.
- **Planned New Treatment**:
  - Student learning journal / progress ledger:
    - Top summary row: "This Week: 24 questions completed • 79% accuracy" with tasteful knowledge-progress illustration.
    - Clean ledger rows with subject markers, date completed, score, and sync status badge.

### 3.18 SettingsScreen (`screens/SettingsScreen.qml`)
- **Current Purpose**: Device configuration menu (Wi-Fi, Sync, Account, Content, Software Update, Diagnostics, About).
- **Business Logic Dependencies**: `appController.navigate()`.
- **Component Dependencies**: `NavRail.qml`, `AppHeader.qml`, `AppCard.qml`.
- **Visual Problems**:
  - Every single row is a floating `AppCard` with 14px radius and icon box. Violates the appliance-style instruction.
- **Planned New Treatment**:
  - Flatter, appliance-like system list:
    - Edge-to-edge clean rows separated by subtle dividers (`#D8D0C1`).
    - Title on left, current value + chevron on right (e.g., `Wi-Fi` ... `Galaxy A33 >`, `Sync` ... `Up to date >`).
    - Minimum 52px row height for effortless touch targets.

### 3.19 WifiScreen (`screens/WifiScreen.qml`)
- **Current Purpose**: Wi-Fi status, scanning, network connection, and password entry.
- **Business Logic Dependencies**: `settingsController.availableNetworks`, `settingsController.scanWifi()`, `settingsController.connectWifi()`, `settingsController.isScanning`, `settingsController.isWifiConnected`.
- **Component Dependencies**: `AppHeader.qml`, `AppCard.qml`, `PrimaryButton.qml`, `StatusBadge.qml`.
- **Visual Problems**:
  - Split-pane with two large white cards. Networks list uses bulky cards.
- **Planned New Treatment**:
  - Native appliance wireless console:
    - Top section: Current status bar (`Wi-Fi [ON]`, connected SSID, signal indicator).
    - Clean network list with Wi-Fi signal strength bars, lock indicator, and connected checkmark.

### 3.20 SyncScreen (`screens/SyncScreen.qml`)
- **Current Purpose**: Student-facing cloud synchronization status and manual trigger.
- **Business Logic Dependencies**: `settingsController.syncStatusSummary`, `settingsController.lastSyncTime`, `settingsController.pendingAttemptsCount`, `settingsController.isSyncing`, `settingsController.startSync()`, `settingsController.automaticSync`, `settingsController.setAutomaticSync()`.
- **Component Dependencies**: `AppHeader.qml`, `AppCard.qml`, `PrimaryButton.qml`, `SecondaryButton.qml`.
- **Visual Problems**:
  - Complex 2x2 technical diagnostic grid inside a large card.
- **Planned New Treatment**:
  - Student-focused calm sync status:
    - Large tactile status: "All caught up" or "3 completed sessions ready to sync".
    - Timestamp: "Last synced 2 minutes ago".
    - Toggle: "Automatic sync [ ON ]".
    - Primary CTA: "Sync now" (Forest Teal). Technical logs moved to Diagnostics.

### 3.21 AccountScreen (`screens/AccountScreen.qml`)
- **Current Purpose**: Linked cloud account info, enrolled study profiles, unlinking option.
- **Business Logic Dependencies**: `settingsController.cloudAccountName`, `settingsController.cloudAccountId`, `settingsController.unlinkDevice()`.
- **Component Dependencies**: `AppHeader.qml`, `AppCard.qml`, `SecondaryButton.qml`.
- **Visual Problems**:
  - Bulky white cards with technical identifiers.
- **Planned New Treatment**:
  - Student-first identity ledger: Account card showing student display name, linked profiles, and safe account options.

### 3.22 ContentScreen (`screens/ContentScreen.qml`)
- **Current Purpose**: Manage installed assessment packs and local storage space.
- **Business Logic Dependencies**: `settingsController.installedPacks`, `settingsController.availablePacks`, `settingsController.storageUsed`, `settingsController.storageTotal`.
- **Component Dependencies**: `AppHeader.qml`, `AppCard.qml`, `ProgressBar.qml`.
- **Visual Problems**:
  - Generic progress bar and card list.
- **Planned New Treatment**:
  - Tactile library bookshelf storage overview: Clean storage gauge ("2.4 GB used of 16 GB") and installed packs list with quick removal/update controls.

### 3.23 SoftwareUpdateScreen (`screens/SoftwareUpdateScreen.qml`)
- **Current Purpose**: Checks for signed OTA updates, shows current version and update progress.
- **Business Logic Dependencies**: `settingsController.currentVersion`, `settingsController.updateStatus`, `settingsController.checkForUpdates()`.
- **Component Dependencies**: `AppHeader.qml`, `AppCard.qml`, `PrimaryButton.qml`.
- **Visual Problems**:
  - White card with technical logs.
- **Planned New Treatment**:
  - Appliance system update screen: Clean current version badge ("v0.1.0"), "Check for Updates" action, and step-by-step verified staging indicator.

### 3.24 DeviceInfoScreen (`screens/DeviceInfoScreen.qml`)
- **Current Purpose**: Displays hardware serial, OS release, app build, and device ID.
- **Business Logic Dependencies**: `settingsController.deviceId`, `settingsController.hardwareModel`, `settingsController.osVersion`.
- **Component Dependencies**: `AppHeader.qml`, `AppCard.qml`.
- **Visual Problems**:
  - Cluttered key-value table inside a card.
- **Planned New Treatment**:
  - Clean specification sheet formatted like a technical book colophon.

### 3.25 DiagnosticsScreen (`screens/DiagnosticsScreen.qml`)
- **Current Purpose**: Hardware checks, database health verification, support bundle export.
- **Business Logic Dependencies**: `settingsController.diagnosticsList`, `settingsController.runDiagnostics()`, `settingsController.exportSupportBundle()`.
- **Component Dependencies**: `AppHeader.qml`, `AppCard.qml`, `PrimaryButton.qml`.
- **Visual Problems**:
  - Dense card with colored badges.
- **Planned New Treatment**:
  - Clean system health checklist with clear status pills (Green Check / Orange Warning) and "Export Support Data" action.

### 3.26 AboutScreen (`screens/AboutScreen.qml`)
- **Current Purpose**: Educational mission, open-source acknowledgments, and software licenses.
- **Business Logic Dependencies**: None (static text + license viewer).
- **Component Dependencies**: `AppHeader.qml`, `AppCard.qml`.
- **Visual Problems**:
  - Text dumped inside a standard card.
- **Planned New Treatment**:
  - Book imprint / colophon style with warm typography, educational mission statement, and clean scrollable license list.

### 3.27 InstituteWorkScreen (`screens/InstituteWorkScreen.qml`)
- **Current Purpose**: Displays teacher/institute assignments assigned to the current study profile.
- **Business Logic Dependencies**: `libraryController.instituteWork`, `libraryController.downloadAssignment()`.
- **Component Dependencies**: `NavRail.qml`, `AppHeader.qml`, `AppCard.qml`, `EmptyState.qml`.
- **Visual Problems**:
  - Same repeated white cards with download buttons.
- **Planned New Treatment**:
  - "School Assignments" folder motif with due date badges, teacher notes, and one-tap download action.

---

## 4. Reusable Component Audit

| Existing Component | Current Implementation | Issues Identified | Planned Redesign |
| :--- | :--- | :--- | :--- |
| `AppCard.qml` | Plain white rectangle, 14px radius, 1px border | Overused across 100% of screens; lacks depth, texture, and editorial character | Transform into polymorphic paper card with warm tone, border hierarchy, and optional subtle edge tint |
| `PrimaryButton.qml` | Generic rounded teal rectangle, centered text | Constant teal everywhere; lacks tactile pressed feedback | Editorial action button with deep ink / forest teal, tactile pressed shadow/offset, and icon integration |
| `SecondaryButton.qml`| White rectangle with grey border | Blends into card backgrounds; lacks hierarchy | Warm parchment button with clear border, distinct hover/pressed state, and legible ink typography |
| `IconButton.qml` | Circular button with stroke icon | Small touch target on some screens (<44px) | Ensure minimum 48×48px hitbox, warm circular surface, and accessible focus indicator |
| `QuestionOption.qml` | 2x2 grid rectangle with option badge | Text truncates on long questions; rigid layout | Flexible option item supporting single/multi-line wrap, tactile letter medallion, and non-color check indicator |
| `NavRail.qml` | 110px left rail with 5 vertical tabs | Consumes 110px width; tabs use generic outline icons | Refined tactile nav rail (96–104px) with custom illustrative icons, paper separator line, and clear active tab marker |
| `AppHeader.qml` | 52px top bar with badges and profile name | Cluttered with 3 badges; notifications overlap header | Clean, calm educational banner with profile identity, non-intrusive status, and integrated back navigation |
| `ProgressBar.qml` | Simple rounded horizontal bar | Flat and synthetic | Two-tone paper progress rail with smooth easing and ink tick marks |
| `StatusBadge.qml` | Rounded pill with colored text and background | Looks like a SaaS status tag | Compact indicator with distinct symbol + text (never color alone) |
| `LoadingState.qml` | Spinner inside text column | Standard web spinner | Calm educational breathing icon / rotating sunburst motif |
| `EmptyState.qml` | Card with circle icon and description | Bland and discouraging | Tasteful educational illustration (empty desk / open map) + friendly guidance CTA |
| `ErrorState.qml` | Pink box with exclamation | Alarming and harsh | Reassuring editorial notice with actionable recovery step |
| `SubmitConfirmModal.qml` | Center dialog with counts | Dry numbers table | Clear pre-submission summary parchment with "Submit Practice" and "Review Questions" |
| `LeaveConfirmModal.qml` | Center dialog with exit warning | Abrupt modal | Gentle pause reminder: "Your progress is saved on this Pi" |
| `PinModal.qml` | 4-digit input pad | Generic keypad | Tactile numeric lock pad with discrete pin dots and clear error message |
| `VirtualKeyboard.qml` | On-screen QWERTY touch keyboard | Basic rectangular keys | Responsive tactile touch keyboard with 48px key targets, distinct shift/backspace/space, and submit key |

---

## 5. Architectural & Design System Redesign Plan

### 5.1 Design System Modules
We will decompose the design tokens into dedicated, modular QML singletons:
1. `Theme.qml`: Core color palette matching the requested reference:
   - Paper / Canvas: `#F5EFE3`
   - Warm Surface: `#FBF7EF`
   - Deep Ink: `#23302D`
   - Muted Ink: `#68716B`
   - Forest / Teal: `#27685E`
   - Soft Sage: `#A9C4B1`
   - Terracotta: `#C76848`
   - Warm Gold: `#D5A64A`
   - Soft Sky: `#A9C7CF`
   - Border: `#D8D0C1`
2. `Typography.qml`: Type hierarchy for 800×480:
   - Hero: 28–30 px
   - Page Title: 22–24 px
   - Question: 20–22 px
   - Section Title: 17–18 px
   - Body: 15–16 px
   - Metadata / Caption: 12–14 px
3. `Spacing.qml`: Standard 4/8/12/16/20/24 px scales.
4. `Metrics.qml`: Touch targets (≥ 48px), radius tokens, component dimensions.
5. `Assets.qml`: Centralized catalog of illustrations, subject artwork, decorative elements, and icons.

### 5.2 Illustration & Graphic Asset Library
Original, lightweight SVG vector assets to be created in `app/ui_qt/assets/`:
- `illustrations/`:
  - `home_hero.svg`: Illustrated educational scene (open book, study lamp, desk, telescope, botanical motif).
  - `celebration_laurel.svg`: Restrained academic laurel and progress ribbon for Results screen.
  - `empty_library.svg`: Tactile empty bookshelf / knowledge path for Empty states.
  - `recovery_lantern.svg`: Reassuring lantern/guide illustration for Recovery.
  - `pairing_device.svg`: Pi device communicating with cloud book.
- `subjects/`:
  - `subject_biology.svg`: Botanical leaf, cell structure, DNA spiral artwork.
  - `subject_chemistry.svg`: Flask, atom, molecular bond reaction artwork.
  - `subject_math.svg`: Geometric compass, coordinate graph, mathematical symbols.
  - `subject_science.svg`: Telescope, planetary orbit, prism artwork.
- `decorative/`:
  - `paper_separator.svg`: Subtle decorative paper-cut divider rule.
  - `confidence_sure.svg`: Bullseye / star of confidence.
  - `confidence_unsure.svg`: Balanced scale / branching choice.
  - `confidence_guess.svg`: Exploratory compass / dice.

### 5.3 Safe Non-Breaking Integration
All existing controller signals, properties, and slots will remain 100% compatible. No assessment engine, database query, sync worker, or profile switching logic will be altered.
Visual redesign will be verified across 800×480 and 800×600 using offscreen image capture and visual inspection.
