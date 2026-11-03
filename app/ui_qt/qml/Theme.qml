pragma Singleton
import QtQuick 2.15

QtObject {
    id: theme

    // -------------------------------------------------------------------------
    // Primary Editorial Palette (Paper / Ink / Nature)
    // -------------------------------------------------------------------------
    readonly property color canvas: "#F5EFE3"          // Paper / Canvas base
    readonly property color background: "#F5EFE3"      // Primary app background
    readonly property color surface: "#FBF7EF"         // Warm Surface for cards / sheets
    readonly property color surfaceElevated: "#FFFFFF" // Crisp white highlights
    readonly property color surfaceActive: "#EFE8D8"   // Pressed / active tactile paper
    readonly property color surfaceSelected: "#EEF5F0" // Soft sage selected tint

    // Deep Ink & Text Hierarchy
    readonly property color deepInk: "#23302D"         // Deep Ink for headlines and primary text
    readonly property color textPrimary: "#23302D"
    readonly property color mutedInk: "#68716B"        // Muted Ink for subtext / metadata
    readonly property color textSecondary: "#68716B"
    readonly property color textMuted: "#8C9690"
    readonly property color textOnPrimary: "#FBF7EF"

    // Subject & Educational Accents
    readonly property color forest: "#27685E"          // Forest / Teal primary action & Biology
    readonly property color primary: "#27685E"
    readonly property color primaryDark: "#1B4B43"     // Deep forest pressed
    readonly property color primaryLight: "#E2EFEA"    // Pale sage wash
    readonly property color sage: "#A9C4B1"            // Soft Sage botanical accent
    readonly property color secondary: "#A9C4B1"
    readonly property color terracotta: "#C76848"      // Terracotta - Chemistry / critical alerts
    readonly property color terracottaLight: "#FDF3EE"
    readonly property color gold: "#D5A64A"            // Warm Gold - Mathematics / badges / review
    readonly property color goldLight: "#FAF5E9"
    readonly property color sky: "#A9C7CF"             // Soft Sky - General science / atmosphere
    readonly property color skyLight: "#EFF6F8"

    // Borders & Dividers
    readonly property color border: "#D8D0C1"          // Warm paper border
    readonly property color borderLight: "#EAE4D7"
    readonly property color divider: "#D8D0C1"
    readonly property color borderFocus: "#27685E"     // High-visibility focus ring

    // Semantic States
    readonly property color success: "#2E7D4E"
    readonly property color warning: "#C76848"
    readonly property color error: "#B83A32"
    readonly property color highlight: "#D5A64A"

    // Typography references (for backwards compatibility)
    readonly property int fontSizeHero: 28
    readonly property int fontSizeTitle: 24
    readonly property int fontSizeHeading: 20
    readonly property int fontSizeBody: 16
    readonly property int fontSizeSecondary: 14
    readonly property int fontSizeCaption: 12
    readonly property string fontFamily: "Segoe UI, Noto Sans, Roboto, DejaVu Sans, sans-serif"
    readonly property string fontFamilySerif: "Georgia, DejaVu Serif, Noto Serif, serif"

    // Dimensions & Touch Targets
    readonly property int touchMin: 48
    readonly property int touchNormal: 54
    readonly property int touchLarge: 60
    readonly property int navRailWidth: 96
    readonly property int headerHeight: 46
    readonly property int cardRadius: 12
    readonly property int buttonRadius: 10
    readonly property int pillRadius: 20

    // Animation
    readonly property int animDuration: 150

    // Dynamic Subject Resolvers
    function subjectIcon(subjectName) {
        if (!subjectName) return Assets.general;
        var s = (subjectName + "").toLowerCase();
        if (s.indexOf("bio") !== -1 || s.indexOf("life") !== -1 || s.indexOf("botany") !== -1 || s.indexOf("zoology") !== -1) {
            return Assets.biology;
        }
        if (s.indexOf("chem") !== -1 || s.indexOf("reaction") !== -1 || s.indexOf("element") !== -1) {
            return Assets.chemistry;
        }
        if (s.indexOf("math") !== -1 || s.indexOf("algebra") !== -1 || s.indexOf("geometry") !== -1 || s.indexOf("fraction") !== -1) {
            return Assets.mathematics;
        }
        if (s.indexOf("sci") !== -1 || s.indexOf("physic") !== -1 || s.indexOf("astronomy") !== -1) {
            return Assets.science;
        }
        if (s.indexOf("eng") !== -1 || s.indexOf("lit") !== -1 || s.indexOf("grammar") !== -1) {
            return Assets.english;
        }
        return Assets.general;
    }

    function subjectAccent(subjectName) {
        if (!subjectName) return forest;
        var s = (subjectName + "").toLowerCase();
        if (s.indexOf("bio") !== -1) return forest;
        if (s.indexOf("chem") !== -1) return terracotta;
        if (s.indexOf("math") !== -1) return gold;
        if (s.indexOf("sci") !== -1) return sky;
        return forest;
    }

    function subjectLightAccent(subjectName) {
        if (!subjectName) return primaryLight;
        var s = (subjectName + "").toLowerCase();
        if (s.indexOf("bio") !== -1) return primaryLight;
        if (s.indexOf("chem") !== -1) return terracottaLight;
        if (s.indexOf("math") !== -1) return goldLight;
        if (s.indexOf("sci") !== -1) return skyLight;
        return primaryLight;
    }
}
