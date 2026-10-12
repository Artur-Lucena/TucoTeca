import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

Dialog {
    id: dialog
    objectName: "emulacaoDialog"
    property int gid: 0
    readonly property var emu: hub.emulacao
    readonly property var d: hub.emulacao.dados
    title: "Mods, texturas, cheats e presets"
    anchors.centerIn: parent
    width: Math.min(760, ApplicationWindow.window.width - 60)
    height: Math.min(800, ApplicationWindow.window.height - 60)
    modal: true; standardButtons: Dialog.Close
    onOpened: dialog.emu.carregar(dialog.gid)
    onClosed: dialog.emu.limpar()
    contentItem: ScrollView {
        clip: true; contentWidth: availableWidth
        ColumnLayout {
            width: parent.width; spacing: 12
            Label { text: dialog.d.titulo || "Jogo 3DS"; font.bold: true; font.pixelSize: 18; Layout.fillWidth: true; elide: Text.ElideRight }
            Label {
                visible: hub.emJogo; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.warning
                text: "Um jogo está aberto. Feche-o antes de alterar mods, texturas, cheats ou presets."
            }
            Label { visible: dialog.d.erro.length > 0; text: dialog.d.erro; color: Theme.warning; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            Label { visible: dialog.d.erro.length === 0; text: "MODS (" + dialog.d.tid + ")"; color: Theme.accent; font.bold: true }
            Label { visible: dialog.d.erro.length === 0 && dialog.d.mods.length === 0; text: "Nenhum mod na biblioteca deste jogo. Importe uma pasta LayeredFS (romfs/exefs) ou um arquivo compactado."; color: Theme.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            Repeater {
                model: dialog.d.mods
                RowLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    CheckBox { text: modelData.nome; checked: modelData.ativo; Layout.fillWidth: true; enabled: !hub.ocupado && !hub.emJogo; onToggled: dialog.emu.alternarMod(modelData.nome) }
                    ActionButton { text: "Remover"; enabled: !hub.ocupado && !hub.emJogo; onClicked: dialog.emu.removerMod(modelData.nome) }
                }
            }
            RowLayout {
                visible: dialog.d.erro.length === 0
                ActionButton { text: dialog.d.mods_off ? "Ligar mods" : "Desligar mods"; enabled: !hub.ocupado && !hub.emJogo; onClicked: dialog.emu.alternarModsOff() }
                ActionButton { text: "Importar pasta de mod…"; enabled: !hub.ocupado && !hub.emJogo; onClicked: modFolder.open() }
                ActionButton { text: "Importar arquivo de mod…"; enabled: !hub.ocupado && !hub.emJogo; onClicked: modFile.open() }
            }
            Label { visible: dialog.d.erro.length === 0; text: "TEXTURAS HD"; color: Theme.accent; font.bold: true }
            Label {
                visible: dialog.d.erro.length === 0; Layout.fillWidth: true; wrapMode: Text.WordWrap
                text: dialog.d.textura.instalado ? dialog.d.textura.arquivos + " arquivos · " + (dialog.d.textura.ativo ? "ligadas" : "desligadas") : "Nenhum pacote de texturas para este jogo."
            }
            RowLayout {
                visible: dialog.d.erro.length === 0
                ActionButton { visible: dialog.d.textura.instalado; text: dialog.d.textura.ativo ? "Desligar texturas" : "Ligar texturas"; enabled: !hub.ocupado && !hub.emJogo; onClicked: dialog.emu.alternarTextura() }
                ActionButton { text: "Instalar pasta de texturas…"; enabled: !hub.ocupado && !hub.emJogo; onClicked: texFolder.open() }
            }
            Label { visible: dialog.d.erro.length === 0; text: "CHEATS (valem depois de reiniciar o jogo)"; color: Theme.accent; font.bold: true }
            Repeater {
                model: dialog.d.cheats
                RowLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    CheckBox { text: modelData.nome + " · " + modelData.linhas + " linhas"; checked: modelData.ativo; Layout.fillWidth: true; enabled: !hub.ocupado && !hub.emJogo; onToggled: dialog.emu.alternarCheat(modelData.nome) }
                    ActionButton { text: "Remover"; enabled: !hub.ocupado && !hub.emJogo; onClicked: dialog.emu.removerCheat(modelData.nome) }
                }
            }
            TextField { id: cheatNome; visible: dialog.d.erro.length === 0; Layout.fillWidth: true; placeholderText: "Nome do cheat"; selectByMouse: true }
            TextArea { id: cheatCodigo; visible: dialog.d.erro.length === 0; Layout.fillWidth: true; Layout.preferredHeight: 90; wrapMode: TextEdit.Wrap; selectByMouse: true; placeholderText: "Códigos XXXXXXXX YYYYYYYY, um por linha" }
            ActionButton {
                visible: dialog.d.erro.length === 0; text: "Salvar cheat (desligado)"
                enabled: !hub.ocupado && cheatNome.text.length > 0 && cheatCodigo.text.length > 0
                onClicked: dialog.emu.adicionarCheat(cheatNome.text, cheatCodigo.text)
            }
            Label { visible: dialog.d.erro.length === 0; text: "PRESETS DO AZAHAR (feche o Azahar antes de aplicar)"; color: Theme.accent; font.bold: true }
            Repeater {
                model: dialog.d.presets
                RowLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    Label { text: modelData; Layout.fillWidth: true; elide: Text.ElideRight }
                    ActionButton { text: "Aplicar"; enabled: !hub.ocupado && !hub.emJogo; onClicked: dialog.emu.aplicarPreset(modelData) }
                }
            }
            RowLayout {
                visible: dialog.d.erro.length === 0
                TextField { id: presetNome; Layout.fillWidth: true; placeholderText: "Nome do preset (fotografa a config atual)"; selectByMouse: true }
                ActionButton { text: "Salvar atual"; enabled: !hub.ocupado && presetNome.text.length > 0; onClicked: dialog.emu.salvarPreset(presetNome.text) }
            }
            Label {
                visible: dialog.d.erro.length === 0; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.accent; font.bold: true
                text: "CONTROLES · XInput agora: " + (hub.controlesConectados.length ? hub.controlesConectados.join(", ") : "nenhum")
            }
            Repeater {
                model: dialog.d.presets_controle
                RowLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    Label { text: modelData; Layout.fillWidth: true; elide: Text.ElideRight }
                    ActionButton { text: "Aplicar"; enabled: !hub.ocupado && !hub.emJogo; onClicked: dialog.emu.aplicarPresetControle(modelData) }
                }
            }
            RowLayout {
                visible: dialog.d.erro.length === 0
                TextField { id: presetControleNome; Layout.fillWidth: true; placeholderText: "Nome do perfil de controles (fotografa o atual)"; selectByMouse: true }
                ActionButton { text: "Salvar perfil atual"; enabled: !hub.ocupado && presetControleNome.text.length > 0; onClicked: dialog.emu.salvarPresetControle(presetControleNome.text) }
            }
        }
    }
    FolderDialog { id: modFolder; title: "Pasta do mod (LayeredFS)"; onAccepted: dialog.emu.importarMod(selectedFolder) }
    FileDialog { id: modFile; title: "Arquivo do mod"; nameFilters: ["Mods (*.zip *.rar *.7z)"]; onAccepted: dialog.emu.importarMod(selectedFile) }
    FolderDialog { id: texFolder; title: "Pasta de texturas (PNG)"; onAccepted: dialog.emu.instalarTextura(selectedFolder) }

    MessageDialog {
        id: confirmar
        title: ""
        text: ""
        buttons: MessageDialog.Yes | MessageDialog.No
        property string chave: ""
        onConfirmed: { dialog.emu.confirmarAcao(confirmar.chave); confirmar.close() }
        onRejected: { dialog.emu.cancelarAcao(confirmar.chave); confirmar.close() }
    }
    Connections {
        target: dialog.emu
        function onConfirmar(titulo, texto, chave) {
            confirmar.title = titulo
            confirmar.text = texto
            confirmar.chave = chave
            confirmar.open()
        }
    }
}
