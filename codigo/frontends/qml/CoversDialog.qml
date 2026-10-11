import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: dialog
    objectName: "coversDialog"
    property string category: "jogos"
    property int ident: 0
    property string itemTitle: ""
    signal configureProviders()
    title: "Buscar capa — " + itemTitle
    anchors.centerIn: parent
    width: Math.min(850, ApplicationWindow.window ? ApplicationWindow.window.width - 60 : parent.width - 60)
    height: Math.min(650, ApplicationWindow.window ? ApplicationWindow.window.height - 40 : parent.height - 40)
    modal: true; standardButtons: Dialog.Close
    onOpened: { provider.currentIndex = 0; hub.buscarCapas(category, ident, "todos", false) }
    contentItem: ColumnLayout {
        spacing: 14
        RowLayout {
            Layout.fillWidth: true
            ComboBox {
                id: provider
                Layout.fillWidth: true
                model: dialog.category === "jogos" ? ["Todas as bibliotecas", "Steam", "SteamGridDB", "Wikipedia"] : ["Todas as bibliotecas", "iTunes", "MusicBrainz / CAA", "Deezer"]
                property var keys: dialog.category === "jogos" ? ["todos", "steam", "steamgriddb", "wikipedia"] : ["todos", "itunes", "musicbrainz", "deezer"]
                onActivated: hub.buscarCapas(dialog.category, dialog.ident, keys[currentIndex], false)
            }
            ActionButton { text: "Atualizar pesquisa"; enabled: !hub.ocupado; onClicked: hub.buscarCapas(dialog.category, dialog.ident, provider.keys[provider.currentIndex], true) }
            ActionButton { text: "Chaves…"; onClicked: dialog.configureProviders() }
        }
        GridView {
            id: arts
            objectName: "coverCandidates"
            Layout.fillWidth: true; Layout.fillHeight: true
            model: hub.capasResultados; clip: true
            cellWidth: width / Math.max(1, Math.floor(width / 200)); cellHeight: 280
            ScrollBar.vertical: ScrollBar {}
            delegate: Rectangle {
                required property var item
                required property int index
                width: arts.cellWidth - 10; height: arts.cellHeight - 10
                radius: 10; color: Theme.surface
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 10; spacing: 8
                    Image { source: item.preview_url; asynchronous: true; fillMode: Image.PreserveAspectFit; Layout.fillWidth: true; Layout.fillHeight: true; sourceSize: Qt.size(300, 380) }
                    Label { text: item.fonte; font.bold: true; color: Theme.accent }
                    Label { text: item.titulo; Layout.fillWidth: true; elide: Text.ElideRight }
                    ActionButton { text: "Usar esta capa"; Layout.fillWidth: true; enabled: !hub.ocupado; onClicked: { hub.aplicarCapa(index); dialog.close() } }
                }
            }
        }
        Label { text: "A capa escolhida é salva no Hub para funcionar offline."; color: Theme.muted; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    }
}
