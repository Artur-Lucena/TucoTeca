import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

Dialog {
    id: dialog
    objectName: "mediaToolsDialog"
    title: "Ferramentas de mídia"
    anchors.centerIn: parent
    width: Math.min(800, ApplicationWindow.window.width - 60)
    height: Math.min(720, ApplicationWindow.window.height - 40)
    modal: true; standardButtons: Dialog.Close
    onOpened: hub.consultarMidias()
    contentItem: ColumnLayout {
        spacing: 12
        RowLayout {
            Layout.fillWidth: true
            TextField { id: file; objectName: "mediaFileField"; Layout.fillWidth: true; placeholderText: "Arquivo a editar, equalizar ou reproduzir (opcional)"; selectByMouse: true }
            ActionButton { text: "Escolher…"; onClicked: chooseFile.open() }
            ActionButton { text: "Atualizar"; enabled: !hub.ocupado; onClicked: hub.consultarMidias() }
        }
        Label { text: "Programas externos são detectados no runtime, ambiente ou instalação local. O botão Abrir usa o arquivo selecionado; sem arquivo, abre o programa."; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.muted }
        ScrollView {
            Layout.fillWidth: true; Layout.fillHeight: true; contentWidth: availableWidth; clip: true
            ColumnLayout {
                width: parent.width; spacing: 14
                Repeater {
                    model: [{key: "imagens", title: "Imagem"}, {key: "equalizadores", title: "Áudio"}, {key: "videos", title: "Reprodutores de vídeo"}]
                    ColumnLayout {
                        required property var modelData
                        Layout.fillWidth: true; spacing: 8
                        Label { text: modelData.title; font.bold: true; color: Theme.accent }
                        Repeater {
                            model: Object.keys(hub.midiasStatus[modelData.key] || {})
                            RowLayout {
                                required property string modelData
                                property var group: parent.modelData
                                property var info: hub.midiasStatus[group.key][modelData]
                                Layout.fillWidth: true
                                Label { text: info.nome + " · " + (info.instalado ? "Instalado" : info.suportado === false ? "Indisponível neste SO" : "Não instalado"); Layout.fillWidth: true; wrapMode: Text.WordWrap }
                                ActionButton { text: "Site ↗"; onClicked: hub.abrirUrl(info.site) }
                                ActionButton { text: "Abrir"; enabled: info.instalado && !hub.ocupado; onClicked: hub.abrirFerramentaMidia(group.key, modelData, file.text) }
                            }
                        }
                    }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Label { text: "Cópia equalizada" }
            ComboBox { id: preset; Layout.fillWidth: true; model: hub.midiasStatus.eq_presets }
            ActionButton { text: "Gerar e importar"; primary: true; enabled: file.text.length > 0 && preset.currentText.length > 0 && !hub.ocupado; onClicked: hub.aplicarEqualizacao(file.text, preset.currentText) }
        }
        Label { text: "A equalização gera uma cópia e a adiciona às músicas do Hub; o original permanece preservado."; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.muted }
    }
    FileDialog { id: chooseFile; title: "Arquivo de mídia"; onAccepted: file.text = decodeURIComponent(selectedFile.toString().replace(Qt.platform.os === "windows" ? /^file:\/\/\// : /^file:\/\//, "")) }
}
