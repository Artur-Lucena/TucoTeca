import QtQuick
import QtQuick.Controls

Button {
    id: control
    property bool primary: false
    property bool selected: false
    property bool quiet: false
    // Variante secundária (chips de filtro, ações pequenas): mesma pílula,
    // 12px mais baixa e texto auxiliar. Sem altura mágica por tela.
    property bool compact: false
    // Altura e texto vêm do Theme (btnAlto/btnTexto); o raio em pílula
    // (altura/2) vale para qualquer altura, inclusive ênfases pontuais.
    implicitHeight: Theme.btnAlto - (control.compact ? 12 : 0)
    implicitWidth: Math.max(control.implicitHeight, label.implicitWidth + (control.compact ? 14 : Theme.btnMargem) * 2)
    padding: 12
    leftPadding: control.compact ? 14 : Theme.btnMargem
    rightPadding: control.compact ? 14 : Theme.btnMargem
    hoverEnabled: true
    font.family: Theme.family
    font.pixelSize: control.compact ? Theme.subtitle : Theme.btnTexto
    font.weight: Font.DemiBold
    opacity: enabled ? 1 : 0.4
    Accessible.name: text
    contentItem: Text {
        id: label
        text: control.text
        font: control.font
        color: control.primary ? Theme.ink : control.selected ? Theme.accent : Theme.text
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    background: Rectangle {
        radius: control.height / 2
        color: control.primary ? (control.hovered ? "#9be7ff" : Theme.accent) :
               control.down || control.selected ? Theme.hover :
               control.hovered ? Theme.raised : control.quiet ? "transparent" : Theme.surface
        border.width: control.activeFocus ? 2 : 1
        border.color: control.activeFocus ? Theme.accent : control.quiet ? "transparent" : Theme.line
        Behavior on color { ColorAnimation { duration: Theme.motion } }
    }
}
