import QtQuick
import QtQuick.Controls

Button {
    id: control
    property bool primary: false
    property bool selected: false
    property bool quiet: false
    implicitHeight: 42
    implicitWidth: Math.max(42, label.implicitWidth + 30)
    padding: 12
    hoverEnabled: true
    font.family: Theme.family
    font.pixelSize: 13
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
        radius: 10
        color: control.primary ? (control.hovered ? "#9be7ff" : Theme.accent) :
               control.down || control.selected ? Theme.hover :
               control.hovered ? Theme.raised : control.quiet ? "transparent" : Theme.surface
        border.width: control.activeFocus ? 2 : 1
        border.color: control.activeFocus ? Theme.accent : control.quiet ? "transparent" : Theme.line
        Behavior on color { ColorAnimation { duration: Theme.motion } }
    }
}
