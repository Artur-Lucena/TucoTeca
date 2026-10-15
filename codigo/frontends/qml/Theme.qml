pragma Singleton
import QtQuick

QtObject {
    // "escuro" (padrao) ou "claro"; densidade: compacto|conforto|bigpicture
    property string tema: "escuro"
    property string densidade: "conforto"
    // Escala de texto configuravel (0.8–1.5); aplica em TODOS os tamanhos.
    property real escala: 1.0
    function fs(n) { return Math.max(8, Math.round(n * escala)) }

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
    readonly property int title: fs(densidade === "bigpicture" ? 38 : 30)
    readonly property int display: fs(densidade === "bigpicture" ? 44 : densidade === "compacto" ? 32 : 36)
    readonly property int headline: fs(densidade === "bigpicture" ? 32 : densidade === "compacto" ? 22 : 25)
    readonly property int subtitle: fs(densidade === "compacto" ? 13 : 14)
    readonly property int card: fs(densidade === "compacto" ? 14 : 15)
    readonly property int meta: fs(densidade === "compacto" ? 12 : 13)
    readonly property int kicker: fs(12)
    // Botões: pílula (raio = altura/2 no ActionButton), altos e com texto
    // legível; uma fonte só — sem altura mágica por tela.
    readonly property int btnAlto: fs(densidade === "bigpicture" ? 54 : densidade === "compacto" ? 44 : 48)
    readonly property int btnTexto: fs(densidade === "bigpicture" ? 16 : densidade === "compacto" ? 14 : 15)
    readonly property int btnMargem: fs(20)
}
