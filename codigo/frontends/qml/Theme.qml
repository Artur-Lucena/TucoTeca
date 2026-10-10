pragma Singleton
import QtQuick

QtObject {
    readonly property color bg: "#0b1019"
    readonly property color surface: "#131c2a"
    readonly property color raised: "#1b283b"
    readonly property color hover: "#24364e"
    readonly property color line: "#2a3b51"
    readonly property color text: "#f4f7fc"
    readonly property color muted: "#a2b2c8"
    readonly property color accent: "#6cd5f5"
    readonly property color ink: "#082332"
    readonly property color positive: "#7ce3b8"
    readonly property color danger: "#ff9eaa"
    readonly property string family: Qt.platform.os === "windows" ? "Segoe UI" : "Sans Serif"
    readonly property int radius: 16
    readonly property int radiusSmall: 10
    readonly property int motion: 160
    readonly property int pad: 18
    readonly property int gap: 14
    readonly property int title: 30
    readonly property int subtitle: 12
    readonly property int card: 14
}
