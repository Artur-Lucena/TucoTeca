pragma Singleton
import QtQuick

QtObject {
    // "escuro" (padrao) ou "claro"; densidade: compacto|conforto|bigpicture
    property string tema: "escuro"
    property string densidade: "conforto"

    readonly property color bg: tema === "claro" ? "#eef2f8" : "#0b1019"
    readonly property color surface: tema === "claro" ? "#ffffff" : "#131c2a"
    readonly property color raised: tema === "claro" ? "#f4f7fc" : "#1b283b"
    readonly property color hover: tema === "claro" ? "#e4ecf7" : "#24364e"
    readonly property color line: tema === "claro" ? "#c9d6e6" : "#2a3b51"
    readonly property color text: tema === "claro" ? "#101827" : "#f4f7fc"
    readonly property color muted: tema === "claro" ? "#4a5a70" : "#a2b2c8"
    readonly property color accent: tema === "claro" ? "#0e7fa8" : "#6cd5f5"
    readonly property color ink: tema === "claro" ? "#ffffff" : "#082332"
    readonly property color positive: tema === "claro" ? "#0d7a54" : "#7ce3b8"
    readonly property color danger: tema === "claro" ? "#b3264a" : "#ff9eaa"
    readonly property color warning: tema === "claro" ? "#8a6116" : "#f0c47b"
    readonly property string family: Qt.platform.os === "windows" ? "Segoe UI" : "Sans Serif"
    readonly property int radius: 16
    readonly property int radiusSmall: 10
    readonly property int motion: 160
    readonly property int pad: densidade === "compacto" ? 12 : 18
    readonly property int gap: densidade === "compacto" ? 9 : 14
    readonly property int title: densidade === "bigpicture" ? 38 : 30
    readonly property int subtitle: densidade === "compacto" ? 13 : 14
    readonly property int card: densidade === "compacto" ? 14 : 15
    readonly property int meta: densidade === "compacto" ? 12 : 13
    readonly property int kicker: 12
}
