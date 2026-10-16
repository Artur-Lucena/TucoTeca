import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

ScrollView {
    id: section
    property var shell
    clip: true; contentWidth: availableWidth
    GridLayout {
        width: parent.width
        columns: section.shell.width >= 1250 ? 3 : 2
        columnSpacing: 18; rowSpacing: 18
        Repeater {
            model: hub.integracoes
            Rectangle {
                id: integrationCard
                required property var modelData
                Layout.fillWidth: true; Layout.preferredHeight: 238
                radius: Theme.radius
                color: integHover.hovered ? Theme.raised : Theme.surface
                border.color: integHover.hovered ? Theme.accentAlt : Theme.line
                HoverHandler { id: integHover }
                Behavior on color { ColorAnimation { duration: Theme.motion } }
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 23; spacing: 12
                    RowLayout {
                        Rectangle { width: 44; height: 44; radius: 13; color: Theme.raised; Text { anchors.centerIn: parent; text: modelData.inicial; color: modelData.cor; font { pixelSize: Theme.fs(18); weight: Font.Bold } } }
                        Item { Layout.fillWidth: true }
                        Text { text: modelData.personalizada ? "SUA" : modelData.tipo === "catalogo" ? "SOB DEMANDA" : "LOCAL"; color: Theme.muted; font { pixelSize: Theme.fs(12); letterSpacing: 1 } }
                    }
                    Text { text: modelData.nome; color: Theme.text; font { pixelSize: Theme.fs(21); weight: Font.DemiBold } }
                    Text { text: modelData.descricao; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.muted; font.pixelSize: Theme.fs(14) }
                    Item { Layout.fillHeight: true }
                    ActionButton { text: modelData.url ? "Abrir →" : modelData.tipo === "catalogo" ? "Explorar catálogo →" : modelData.tipo === "download" ? "Ver downloads →" : modelData.tipo === "musicas_online" ? "Escolher músicas →" : modelData.tipo === "provedores" ? "Configurar provedores →" : "Gerenciar emulador →"; Layout.fillWidth: true; onClicked: section.shell.useIntegration(modelData) }
                    ActionButton { visible: modelData.personalizada; text: "Remover"; quiet: true; Layout.fillWidth: true; onClicked: hub.removerIntegracao(modelData.chave) }
                }
            }
        }
    }
}
