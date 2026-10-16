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
        id: fundo
        radius: control.height / 2
        color: control.primary ? Theme.accent :
               control.down || control.selected ? Theme.hover :
               control.hovered ? Theme.raised : control.quiet ? "transparent" : Theme.surface
        border.width: control.activeFocus ? 2 :
                      control.quiet && !control.hovered && !control.down && !control.selected ? 0 : 1
        border.color: control.activeFocus ? Theme.accent :
                      control.selected ? Theme.accent :
                      control.primary ? "transparent" : Theme.line
        Behavior on color { ColorAnimation { duration: Theme.motion } }
        // Gradiente sutil accent -> accentAlt; só no primário, por cima da cor
        // (mantém raio em pílula e o mesmo fundo lido pelos testes).
        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            visible: control.primary
            opacity: control.hovered ? 1 : 0.88
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0; color: Theme.accent }
                GradientStop { position: 1; color: Theme.accentAlt }
            }
            Behavior on opacity { NumberAnimation { duration: Theme.motion } }
        }
    }
}
