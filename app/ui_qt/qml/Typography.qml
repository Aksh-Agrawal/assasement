pragma Singleton
import QtQuick 2.15

QtObject {
    id: typography

    // Font Families
    readonly property string family: "Segoe UI, Noto Sans, Roboto, DejaVu Sans, sans-serif"
    readonly property string fontFamily: family
    readonly property string familyEditorial: "Georgia, DejaVu Serif, Noto Serif, Segoe UI, serif"
    readonly property string fontSerif: familyEditorial

    // Type Scale (optimized for 800x480 at ~180 DPI)
    readonly property int hero: 28
    readonly property int heroTitle: hero
    readonly property int pageTitle: 24
    readonly property int question: 21
    readonly property int sectionTitle: 18
    readonly property int body: 16
    readonly property int metadata: 13
    readonly property int caption: 12

    // Font Weights
    readonly property int weightNormal: Font.Normal
    readonly property int weightMedium: Font.DemiBold
    readonly property int weightBold: Font.Bold
}
