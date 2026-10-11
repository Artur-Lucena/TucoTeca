import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

Dialog {
    id: dialog
    objectName: "gameToolsDialog"
    property int gid: 0
    property bool carregou: false
    property string snapshotEscolhido: ""
    title: "Saves, imagens e organização"
    anchors.centerIn: parent
    width: Math.min(740, ApplicationWindow.window.width - 60)
    height: Math.min(760, ApplicationWindow.window.height - 60)
    modal: true; standardButtons: Dialog.Close
    onOpened: { carregou = false; hub.consultarFerramentasJogo(gid) }
    onClosed: hub.consultarFerramentasJogo(0)
    Connections {
        target: hub
        function onFerramentasMudou() {
            if (dialog.visible && !dialog.carregou) {
                savePaths.text = hub.ferramentasJogo.saves.join("\n")
                dialog.carregou = true
            }
        }
    }
    contentItem: ScrollView {
        clip: true; contentWidth: availableWidth
        ColumnLayout {
            width: parent.width; spacing: 12
            Label { text: "SAVES DO JOGO"; color: Theme.accent; font.bold: true }
            Label { text: "Informe os arquivos/pastas de saves (um caminho por linha). O snapshot copia os saves; nunca altera o original."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            TextArea { id: savePaths; objectName: "savePathsField"; Layout.fillWidth: true; Layout.preferredHeight: 90; wrapMode: TextEdit.Wrap; selectByMouse: true; placeholderText: "C:\\Users\\…\\Saved Games\\Meu Jogo" }
            RowLayout {
                ActionButton { text: "Escolher pasta…"; onClicked: saveFolder.open() }
                ActionButton { text: "Salvar caminhos"; enabled: !hub.ocupado; onClicked: hub.configurarSaves(dialog.gid, savePaths.text) }
                ActionButton { text: "Snapshot agora"; enabled: !hub.ocupado; onClicked: hub.snapshotSaves(dialog.gid) }
            }
            Repeater {
                model: hub.ferramentasJogo.snapshots
                RowLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    Label { text: modelData.nome; Layout.fillWidth: true; elide: Text.ElideRight }
                    ActionButton { text: "Abrir pasta"; onClicked: hub.abrirPasta(modelData.path) }
                    ActionButton { text: "Restaurar…"; enabled: !hub.ocupado && !hub.emJogo; onClicked: { dialog.snapshotEscolhido = modelData.path; restoreConfirm.open() } }
                }
            }
            Label { text: "SCREENSHOTS"; color: Theme.accent; font.bold: true }
            ActionButton { text: "Abrir pasta vigiada de imagens"; Layout.fillWidth: true; onClicked: hub.abrirPasta(hub.ferramentasJogo.pasta_screenshots) }
            Flow {
                Layout.fillWidth: true; Layout.preferredHeight: childrenRect.height
                spacing: 8
                Repeater {
                    model: hub.ferramentasJogo.screenshots
                    Image { required property var modelData; width: 140; height: 90; source: modelData.url; sourceSize: Qt.size(280, 180); fillMode: Image.PreserveAspectFit; asynchronous: true; ToolTip.visible: imageHover.hovered; ToolTip.text: modelData.nome; HoverHandler { id: imageHover } }
                }
            }
            Label { text: "PATCH IPS/BPS — NOVA ROM"; color: Theme.accent; font.bold: true }
            TextField { id: rom; Layout.fillWidth: true; placeholderText: "ROM original"; selectByMouse: true }
            TextField { id: patchRom; Layout.fillWidth: true; placeholderText: "Arquivo .ips ou .bps"; selectByMouse: true }
            TextField { id: outputRom; Layout.fillWidth: true; placeholderText: "Caminho de saída (arquivo novo)"; selectByMouse: true }
            RowLayout {
                ActionButton { text: "ROM…"; onClicked: romFile.open() }
                ActionButton { text: "Patch…"; onClicked: patchFile.open() }
                ActionButton { text: "Aplicar em cópia"; enabled: !hub.ocupado && rom.text && patchRom.text && outputRom.text; onClicked: hub.aplicarPatchRom(rom.text, patchRom.text, outputRom.text) }
            }
            Label { text: "ORGANIZAR SEM APAGAR A ORIGEM"; color: Theme.accent; font.bold: true }
            TextField { id: sourceFolder; Layout.fillWidth: true; placeholderText: "Pasta de origem"; selectByMouse: true }
            TextField { id: targetFolder; Layout.fillWidth: true; placeholderText: "Nova pasta de destino"; selectByMouse: true }
            CheckBox { id: hardlinks; text: "Usar hardlinks (compartilham alterações; não são backup)"; Layout.fillWidth: true }
            ActionButton { text: "Copiar/ligar arquivos"; Layout.fillWidth: true; enabled: !hub.ocupado && sourceFolder.text && targetFolder.text; onClicked: hub.copiarJogo(sourceFolder.text, targetFolder.text, hardlinks.checked) }
            ActionButton { text: "Medir espaço em disco deste jogo"; Layout.fillWidth: true; enabled: !hub.ocupado; onClicked: hub.medirDiscoJogo(dialog.gid) }
        }
    }
    FolderDialog { id: saveFolder; title: "Escolha a pasta de saves"; onAccepted: savePaths.text += (savePaths.text ? "\n" : "") + hub.caminhoLocal(selectedFolder) }
    FileDialog { id: romFile; title: "ROM original"; onAccepted: rom.text = hub.caminhoLocal(selectedFile) }
    FileDialog { id: patchFile; title: "Patch IPS/BPS"; nameFilters: ["Patch (*.ips *.bps)"]; onAccepted: patchRom.text = hub.caminhoLocal(selectedFile) }
    Dialog {
        id: restoreConfirm
        anchors.centerIn: parent; modal: true; width: Math.min(480, dialog.width - 40)
        title: "Restaurar progresso?"; standardButtons: Dialog.Ok | Dialog.Cancel
        Label { width: parent.width; wrapMode: Text.WordWrap; text: "Os saves configurados serão substituídos pelos deste snapshot. Os atuais recebem um novo snapshot antes da restauração. O jogo precisa estar fechado." }
        onAccepted: hub.restaurarSaves(dialog.gid, dialog.snapshotEscolhido)
    }
}
