import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

Dialog {
    id: dialog
    objectName: "musicDownloadsDialog"
    title: "Fila de músicas · baixar e importar"
    anchors.centerIn: parent
    width: Math.min(900, ApplicationWindow.window ? ApplicationWindow.window.width - 60 : parent.width - 60)
    height: Math.min(650, ApplicationWindow.window ? ApplicationWindow.window.height - 40 : parent.height - 40)
    modal: true; standardButtons: Dialog.Close
    contentItem: ColumnLayout {
        spacing: 12
        RowLayout {
            Layout.fillWidth: true
            ActionButton { text: "Baixar/importar fila"; primary: true; enabled: !hub.ocupado; onClicked: hub.baixarFilaMusicas() }
            ActionButton { text: "Parar após faixa"; enabled: hub.downloadMusica.rotulo.length > 0 && !hub.downloadMusica.cancelando; onClicked: hub.pararDownloadMusicas() }
            ActionButton { text: "Dependências de áudio"; enabled: !hub.ocupado; onClicked: hub.instalarAudio() }
            ActionButton { text: "Importar CSV…"; enabled: !hub.ocupado; onClicked: csv.open() }
        }
        Label { text: hub.downloadMusica.cancelando ? "Finalizando a faixa atual…" : hub.downloadMusica.rotulo || "Fila persistente. Falhas podem ser retomadas pelo mesmo botão."; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.accent }
        ProgressBar { Layout.fillWidth: true; from: 0; to: 100; value: hub.downloadMusica.pct || 0; visible: hub.downloadMusica.rotulo.length > 0 }
        ListView {
            Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 6
            model: hub.filaMusicas
            ScrollBar.vertical: ScrollBar {}
            delegate: Rectangle {
                required property var modelData
                width: ListView.view.width - 12; height: 90; color: Theme.surface; radius: 10
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 12
                    Label { text: modelData.artista + " — " + modelData.titulo; Layout.fillWidth: true; elide: Text.ElideRight; font.bold: true }
                    Label { text: modelData.id === hub.downloadMusica.id ? "Baixando · " + Math.round(hub.downloadMusica.pct) + "%" : modelData.estado; color: Theme.accent }
                    Label { text: modelData.erro || modelData.album || ""; Layout.fillWidth: true; elide: Text.ElideRight; color: Theme.muted }
                }
            }
        }
        Label { text: "Ao concluir, cada faixa já aparece em Músicas. Importar pasta continua disponível para a coleção do Harmoni."; color: Theme.muted; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    }
    FileDialog { id: csv; title: "CSV Exportify/Harmoni"; nameFilters: ["CSV (*.csv)"]; onAccepted: hub.importarCsvMusicas(selectedFile) }
}
