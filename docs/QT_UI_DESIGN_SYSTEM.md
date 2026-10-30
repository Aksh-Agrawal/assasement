# Qt/QML Production UI Design System

## 1. Overview & Display Geometry

The user interface is designed natively for a **5-inch touchscreen (800 × 480 Landscape)** running on a Raspberry Pi Zero 2 W (512 MB RAM). It also supports responsive expansion for an **800 × 600** development fallback.

- **Primary Geometry**: 800 × 480 pixels (Landscape)
- **Secondary Fallback**: 800 × 600 pixels (Responsive anchors, no vertical letterboxing)
- **Aspect Ratio**: 5:3 native
- **Target Form Factor**: Dedicated, calm, child-safe handheld educational appliance.

---

## 2. Color System & Accessibility

The color palette is derived directly from the "Raspberry Pi Study Buddy" visual identity. It avoids harsh contrasts (pure #000000 or #FFFFFF) to reduce eye strain, while maintaining strict WCAG AA contrast standards (≥ 4.5:1 for body text, ≥ 3:1 for large text).

| Role | Color Name | Hex Code | Purpose / Usage | Contrast Ratio |
| :--- | :--- | :--- | :--- | :--- |
| **Background** | Eggshell | `#F8F4EA` | Primary window and screen background | Base |
| **Surface / Card** | Warm Off-White | `#FFF9F0` | Content cards, question surfaces, modal backgrounds | 1.05:1 vs bg |
| **Surface Highlight** | Soft Sage Tint | `#EDF4EB` | Selected option background, active state tint | Accessible |
| **Primary** | Study Teal | `#2E7D73` | Primary action buttons, active navigation, active borders | 4.8:1 vs bg |
| **Primary Dark** | Forest Teal | `#1E554E` | Pressed button state, high-contrast headings | 7.1:1 vs bg |
| **Secondary** | Soft Sage | `#A7C4A0` | Category badges, friendly secondary accents | Accent |
| **Highlight** | Warm Apricot | `#F4B183` | Flagged for review, secondary highlights, warnings | Accent |
| **Warning / Error** | Terracotta | `#D46B5B` | Critical alerts, unlinking warnings, failure messages | 4.6:1 vs bg |
| **Text Primary** | Deep Charcoal | `#2E2E2E` | Headings, questions, primary labels | 10.4:1 vs bg |
| **Text Secondary** | Muted Charcoal | `#5F6368` | Subtitles, timestamps, metadata, instructions | 4.9:1 vs bg |
| **Success** | Forest Green | `#3B8246` | Sync complete, correct answer review, online indicator | 4.7:1 vs bg |
| **Border / Divider** | Warm Gray | `#E2DCD0` | Card borders, rail divider, list separators | Distinct border |

### Accessibility Rules:
- **No Color-Only Information**: Status badges always combine an icon/symbol and text (e.g., `● Online`, `✓ Ready`, `🚩 Review`).
- **Focus Indicators**: 2px `#2E7D73` border with clear border contrast.
- **Large Text Minimum**: Body text is at least 18px; no critical interface text is below 14px.

---

## 3. Typography Hierarchy

Fonts rely on clean, readable system sans-serif fonts (e.g. Noto Sans, Roboto, DejaVu Sans).

| Level | Size | Weight | Line Height | Usage |
| :--- | :--- | :--- | :--- | :--- |
| **Screen Title** | 26 px | SemiBold / Bold | 32 px | Screen headers, modal titles, greeting |
| **Section Heading** | 22 px | SemiBold | 28 px | Card headers, topic titles, score display |
| **Body / Question** | 18 px | Regular | 26 px | Question text, option text, instructions |
| **Secondary Text** | 15 px | Regular | 20 px | Subtitles, timestamps, metadata |
| **Caption / Status** | 14 px | Medium | 18 px | Badges, rail labels, timer, micro-indicators |

---

## 4. Touch Targets & Component Sizing

Optimized for 5-inch touchscreens where finger tap accuracy requires generous hitboxes.

| Component | Height | Min Width | Corner Radius | Touch Area Padding |
| :--- | :--- | :--- | :--- | :--- |
| **MCQ Option Card** | 58–64 px | Full col width | 14 px | 8 px margin |
| **Primary Action Button** | 54–60 px | 160 px | 14 px | 4 px margin |
| **Secondary Button** | 50–54 px | 140 px | 14 px | 4 px margin |
| **Nav Rail Item** | 62 px | 108 px | 12 px | Full tab width |
| **Icon Button** | 50 px | 50 px | 25 px (circle) | Center target |
| **Settings Row** | 56 px | Full width | 12 px | Edge-to-edge |
| **Review Grid Button** | 52 px | 52 px | 12 px | Grid cell |

---

## 5. Navigation Shell & Architecture

```text
┌─────────────┬────────────────────────────────────────────────────────┐
│  Nav Rail   │ Top Status Bar: Alex • Primary 6      ● Online   Sync✓ │
│  (110 px)   ├────────────────────────────────────────────────────────┤
│             │                                                        │
│  [ Home ]   │                                                        │
│  [Library]  │                   SCREEN CONTENT                       │
│  [Practice] │                   (690 × 424 px)                       │
│  [History]  │                                                        │
│  [Settings] │                                                        │
│             │                                                        │
└─────────────┴────────────────────────────────────────────────────────┘
```

1. **Left Navigation Rail (110 px)**: Present on main discovery screens (`Home`, `Library`, `Practice`, `History`, `Settings`).
2. **Immersive Assessment Mode**: During active test taking (`Question`, `Confidence`, `Navigator`, `Submit Confirm`, `Review`), the **Nav Rail is completely hidden**, providing the full 800 × 480 area for focus and long question texts.
3. **Physical Buttons / Hardware Input**:
   - `Escape` / `Action.BACK` -> Pop StackView / Return to previous screen.
   - `Home` / `Action.HOME` -> Return to student dashboard.
   - Physical GPIO buttons invoke standard controller Actions without tight hardware coupling.

---

## 6. Performance Rules for Raspberry Pi Zero 2 W

To maintain 60 FPS UI responsiveness on 512 MB RAM without CPU spikes:
- **No Qt WebEngine / Chromium**: Zero embedded web views.
- **No Complex Shader Effects**: No multi-pass blur, continuous particle emitters, or real-time drop shadows.
- **Animation Guideline**: Short property transitions of **140–160 ms** using `NumberAnimation` on opacity and position.
- **Resource Discipline**: Solid background colors, lightweight vector SVG icons, lazy QML screen instantiation.
- **Non-Blocking UI**: Background threads own networking and SQLite sync; immutable data models cross to QML via Qt signals and properties.
